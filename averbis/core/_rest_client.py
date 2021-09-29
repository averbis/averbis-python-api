#
# Copyright (c) 2021 Averbis GmbH.
#
# This file is part of Averbis Python API.
# See https://www.averbis.com for further info.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#
#
import copy

from cassis import Cas, TypeSystem, load_cas_from_xmi, load_typesystem  # type: ignore
import json
import logging
import zipfile
import os
from concurrent.futures.thread import ThreadPoolExecutor
from functools import wraps
from io import BytesIO, IOBase, BufferedReader
from json import JSONDecodeError

from time import sleep, time
from typing import List, Union, IO, Iterable, Dict, Iterator, Optional
from pathlib import Path
import requests
import mimetypes

from requests import RequestException

ENCODING_UTF_8 = "utf-8"

HEADER_ACCEPT = "Accept"
HEADER_CONTENT_TYPE = "Content-Type"

MEDIA_TYPE_ANY = "*/*"
MEDIA_TYPE_APPLICATION_XMI = "application/vnd.uima.cas+xmi"
MEDIA_TYPE_APPLICATION_JSON = "application/json"
MEDIA_TYPE_APPLICATION_XML = "application/xml"
MEDIA_TYPE_APPLICATION_ZIP = "application/zip"
MEDIA_TYPE_APPLICATION_SOLR_XML = "application/vnd.averbis.solr+xml"
MEDIA_TYPE_TEXT_PLAIN = "text/plain"
MEDIA_TYPE_TEXT_PLAIN_UTF8 = "text/plain; charset=utf-8"
MEDIA_TYPE_OCTET_STREAM = "application/octet-stream"

DOCUMENT_IMPORTER_CAS = "CAS Importer"
DOCUMENT_IMPORTER_SOLR = "Solr XML Importer"
DOCUMENT_IMPORTER_TEXT = "Text Importer"

TERMINOLOGY_IMPORTER_OBO = "OBO Importer"

TERMINOLOGY_EXPORTER_OBO_1_4 = "Obo 1.4 Exporter"
TERMINOLOGY_EXPORTER_SOLR_AUTO_SUGGEST_XML = "Solr Autosuggest XML Exporter"
TERMINOLOGY_EXPORTER_CONCEPT_DICTIONARY_XML = "Concept Dictionary XML Exporter"


def experimental_api(original_function):
    @wraps(original_function)
    def new_function(*args, **kwargs):
        return original_function(*args, **kwargs)

    return new_function


class OperationNotSupported(Exception):
    """Raised when the REST API does not support a given operation."""

    pass


class OperationTimeoutError(Exception):
    """
    Raised when an operation times out. This can be a simple remote operation or also a complex operation such as
    waiting for a state change.
    """

    pass


class Result:
    def __init__(
        self, data: Dict = None, exception: Exception = None, source: Union[Path, IO, str] = None
    ):
        self.data = data
        self.exception = exception
        if source:
            if isinstance(source, str):
                self.source = source
            elif isinstance(source, Path):
                self.source = str(source)
            else:
                self.source = source.name

    def successful(self):
        return self.exception is None


class Pipeline:
    STATE_STARTED = "STARTED"
    STATE_STARTING = "STARTING"
    STATE_STOPPED = "STOPPED"
    STATE_STOPPING = "STOPPING"

    def __init__(self, project: "Project", name: str):
        self.__logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
        self.project = project
        self.name = name
        self.pipeline_state_poll_interval = 5
        self.pipeline_state_change_timeout = self.pipeline_state_poll_interval * 10
        self.cached_type_system = None

    def __repr__(self):
        return f'{self.__class__.__name__}(name="{self.name}", project="{self.project.name}")'

    def wait_for_pipeline_to_leave_transient_state(self) -> str:
        pipeline_info = self.get_info()
        total_time_slept = 0
        while pipeline_info["pipelineState"] in [self.STATE_STARTING, self.STATE_STOPPING]:
            self.__fail_on_pipeline_error_state(pipeline_info)
            if total_time_slept > self.pipeline_state_change_timeout:
                raise OperationTimeoutError(
                    f"Pipeline stuck in transient state {pipeline_info['pipelineState']} for ${total_time_slept}"
                )
            sleep(self.pipeline_state_poll_interval)
            total_time_slept += self.pipeline_state_poll_interval
            pipeline_info = self.get_info()
        return pipeline_info["pipelineState"]

    def wait_for_pipeline_to_arrive_at_state(self, target_state: str) -> None:
        pipeline_info = self.get_info()
        total_time_slept = 0
        while pipeline_info["pipelineState"] != target_state:
            self.__fail_on_pipeline_error_state(pipeline_info)
            if total_time_slept > self.pipeline_state_change_timeout:
                raise OperationTimeoutError(
                    f"Pipeline did not arrive at state {target_state} after ${total_time_slept}"
                )
            sleep(self.pipeline_state_poll_interval)
            total_time_slept += self.pipeline_state_poll_interval
            pipeline_info = self.get_info()

    @staticmethod
    def __fail_on_pipeline_error_state(pipeline_info) -> None:
        if isinstance(pipeline_info["pipelineStateMessage"], str):
            if "exception" in pipeline_info["pipelineStateMessage"].lower():
                raise Exception(
                    f"Pipeline state change error: {pipeline_info['pipelineStateMessage']}"
                )

    def ensure_started(self) -> "Pipeline":
        """
        Checks if the pipline has started. If the pipeline has not started yet, an attempt will be made to start it. The
        call will block for a certain time. If the time expires without the pipeline becoming available, an exception
        is generated.

        :return: the pipeline object for chaining additional calls.
        """
        state = self.wait_for_pipeline_to_leave_transient_state()
        if state != self.STATE_STARTED:
            self.start()
            self.wait_for_pipeline_to_arrive_at_state(self.STATE_STARTED)
        return self

    def ensure_stopped(self) -> "Pipeline":
        """
        Causes the pipeline on the server to shut done.

        :return: the pipeline object for chaining additional calls.
        """
        state = self.wait_for_pipeline_to_leave_transient_state()
        if state != self.STATE_STOPPED:
            self.stop()
            self.wait_for_pipeline_to_arrive_at_state(self.STATE_STOPPED)
        return self

    def start(self) -> dict:
        """
        Start the server-side pipeline. This call returns immediately. However, the pipeline will usually take a while
        to boot and become available.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._start_pipeline(self.project.name, self.name)

    def stop(self) -> dict:
        """
        Stop the server-side pipeline.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._stop_pipeline(self.project.name, self.name)

    def get_info(self) -> dict:
        """
        Obtain information about the server-side pipeline.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._get_pipeline_info(self.project.name, self.name)

    @experimental_api
    def delete(self) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear. Deletes an existing pipeline from the server.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        if self.project.client.get_spec_version().startswith("5."):
            raise OperationNotSupported(
                "Deleting pipelines is not supported by the REST API in platform version 5.x, but only from 6.x "
                "onwards."
            )

        # noinspection PyProtectedMember
        return self.project.client._delete_pipeline(self.project.name, self.name)

    def is_started(self) -> bool:
        """
        Checks if the pipeline has already started.

        :return: Whether the pipeline has started.
        """
        return self.get_info()["pipelineState"] == "STARTED"

    def analyse_text(
        self,
        source: Union[Path, IO, str],
        annotation_types: str = None,
        language: str = None,
        timeout: float = None,
    ) -> dict:
        """
        Analyze the given text or text file using the pipeline.

        :param source:           The document to be analyzed.
        :param annotation_types: Optional parameter indicating which types should be returned. Supports wildcard expressions, e.g. "de.averbis.types.*" returns all types with prefix "de.averbis.types"
        :param language:         Optional parameter setting the language of the document, e.g. "en" or "de".
        :param timeout:          Optional timeout (in seconds) specifiying how long the request is waiting for a server response.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """

        # noinspection PyProtectedMember
        return self.project.client._analyse_text(
            project=self.project.name,
            pipeline=self.name,
            source=source,
            annotation_types=annotation_types,
            language=language,
            timeout=timeout,
        )

    def analyse_texts(
        self,
        sources: Iterable[Union[Path, IO, str]],
        parallelism: int = 0,
        annotation_types: str = None,
        language: str = None,
        timeout: float = None,
    ) -> Iterator[Result]:
        """
        Analyze the given texts or files using the pipeline. If feasible, multiple documents are processed in parallel.

        :param sources:          The documents to be analyzed.
        :param parallelism:      Number of parallel instances in the platform.
        :param annotation_types: Optional parameter indicating which types should be returned. Supports wildcard expressions, e.g. "de.averbis.types.*" returns all types with prefix "de.averbis.types"
        :param language:         Optional parameter setting the language of the document, e.g. "en" or "de".
        :param timeout:          Optional timeout (in seconds) specifiying how long the request is waiting for a server response.

        :return: An iterator over the results produced by the pipeline.
        """
        if self.project.client.get_spec_version().startswith("5."):
            pipeline_instances = self.get_configuration()["analysisEnginePoolSize"]
        else:
            pipeline_instances = self.get_configuration()["numberOfInstances"]

        if parallelism < 0:
            parallel_request_count = max(pipeline_instances + parallelism, 1)
        elif parallelism > 0:
            parallel_request_count = parallelism
        else:
            parallel_request_count = pipeline_instances

        if parallel_request_count > 1:
            self.__logger.debug(f"Triggering {parallel_request_count} requests in parallel")
        else:
            self.__logger.debug(
                f"Not performing parallel requests (remote supports max {pipeline_instances} parallel requests)"
            )

        def run_analysis(source):
            try:
                return Result(
                    data=self.analyse_text(
                        source=source,
                        annotation_types=annotation_types,
                        language=language,
                        timeout=timeout,
                    ),
                    source=source,
                )
            except Exception as e:
                return Result(exception=e, source=source)

        with ThreadPoolExecutor(max_workers=parallel_request_count) as executor:
            return executor.map(run_analysis, sources)

    def analyse_html(
        self,
        source: Union[Path, IO, str],
        annotation_types: str = None,
        language: str = None,
        timeout: float = None,
    ) -> dict:
        """
        Analyze the given HTML string or HTML file using the pipeline.

        :param source:           The document to be analyzed.
        :param annotation_types: Optional parameter indicating which types should be returned. Supports wildcard expressions, e.g. "de.averbis.types.*" returns all types with prefix "de.averbis.types"
        :param language:         Optional parameter setting the language of the document, e.g. "en" or "de".
        :param timeout:          Optional timeout (in seconds) specifiying how long the request is waiting for a server response.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """

        # noinspection PyProtectedMember
        return self.project.client._analyse_html(
            project=self.project.name,
            pipeline=self.name,
            source=source,
            annotation_types=annotation_types,
            language=language,
            timeout=timeout,
        )

    def get_configuration(self) -> dict:
        """
        Obtain the pipeline configuration.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._get_pipeline_configuration(self.project.name, self.name)

    def set_configuration(self, configuration: dict) -> None:
        """
        Updates the pipeline configuration. If the pipeline is already running, it will be stopped because changes
        to the configuration can only be performed while a pipeline is stopped. If the pipeline was stopped, it
        is restarted after the configuration has been updated. As a side-effect, the cached type system previously
        obtained for this pipeline is cleared.

        :param configuration: a pipeline configuration in the form returned by get_configuration()
        """
        self.cached_type_system = None
        state = self.wait_for_pipeline_to_leave_transient_state()
        was_running_before_configuration_change = False
        if state == self.STATE_STARTED:
            self.ensure_stopped()
        # noinspection PyProtectedMember
        self.project.client._set_pipeline_configuration(self.project.name, self.name, configuration)
        if was_running_before_configuration_change:
            self.ensure_started()

    # Ignoring errors as linter (compiler) cannot resolve dynamically loaded lib
    # (with type:ignore for mypy) and (noinspection PyProtectedMember for pycharm)
    @experimental_api
    def analyse_text_to_cas(
        self,
        source: Union[Path, IO, str],
        annotation_types: str = None,
        language: str = None,
        timeout: float = None,
    ) -> Cas:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear. Processes text using a pipeline and returns the result
        as a UIMA CAS.

        :param source:           The document to be analyzed.
        :param annotation_types: Optional parameter indicating which types should be returned. Supports wildcard expressions, e.g. "de.averbis.types.*" returns all types with prefix "de.averbis.types"
        :param language:         Optional parameter setting the language of the document, e.g. "en" or "de".
        :param timeout:          Optional timeout (in seconds) specifiying how long the request is waiting for a server response.

        :return: A cassis.Cas object
        """
        # noinspection PyProtectedMember
        return load_cas_from_xmi(
            self.project.client._analyse_text_xmi(
                project=self.project.name,
                pipeline=self.name,
                source=source,
                annotation_types=annotation_types,
                language=language,
                timeout=timeout,
            ),
            typesystem=self.get_type_system(),
        )

    @experimental_api
    def analyse_texts_to_cas(
        self,
        sources: Iterable[Union[Path, IO, str]],
        parallelism: int = 0,
        language: str = None,
        timeout: float = None,
    ) -> Iterator[Result]:
        """
        Analyze the given texts or files using the pipeline. If feasible, multiple documents are processed in parallel.

        :param sources:          The documents to be analyzed.
        :param parallelism:      Number of parallel instances in the platform.
        :param language:         Optional parameter setting the language of the document, e.g. "en" or "de".
        :param timeout:          Optional timeout (in seconds) specifiying how long the request is waiting for a server response.

        :return: An iterator over the results produced by the pipeline.
        """
        if self.project.client.get_spec_version().startswith("5."):
            pipeline_instances = self.get_configuration()["analysisEnginePoolSize"]
        else:
            pipeline_instances = self.get_configuration()["numberOfInstances"]

        if parallelism < 0:
            parallel_request_count = max(pipeline_instances + parallelism, 1)
        elif parallelism > 0:
            parallel_request_count = parallelism
        else:
            parallel_request_count = pipeline_instances

        if parallel_request_count > 1:
            self.__logger.debug(f"Triggering {parallel_request_count} requests in parallel")
        else:
            self.__logger.debug(
                f"Not performing parallel requests (remote supports max {pipeline_instances} parallel requests)"
            )

        def run_analysis(source):
            try:
                return Result(
                    data=self.analyse_text_to_cas(
                        source=source,
                        language=language,
                        timeout=timeout,
                    ),
                    source=source,
                )
            except Exception as e:
                return Result(exception=e, source=source)

        with ThreadPoolExecutor(max_workers=parallel_request_count) as executor:
            return executor.map(run_analysis, sources)

    # Ignoring errors as linter (compiler) cannot resolve dynamically loaded lib
    # (with type:ignore for mypy) and (noinspection PyProtectedMember for pycharm)
    @experimental_api
    def get_type_system(self) -> TypeSystem:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear. Processes text using a pipeline and returns the result
        as a UIMA CAS.
        """
        if self.cached_type_system is None:
            # noinspection PyProtectedMember
            self.cached_type_system = load_typesystem(
                self.project.client._get_pipeline_type_system(self.project.name, self.name)
            )
        return self.cached_type_system

    @experimental_api
    def list_resources(self) -> List[str]:
        """
        List the resources of the pipeline.

        :return: The list of pipeline resources.
        """
        # noinspection PyProtectedMember
        return self.project.client._list_resources(
            project_name=self.project.name, pipeline_name=self.name
        )["files"]

    @experimental_api
    def delete_resources(self) -> None:
        """
        Delete the resources of the pipeline.
        """
        # noinspection PyProtectedMember
        self.project.client._delete_resources(
            project_name=self.project.name, pipeline_name=self.name
        )

    @experimental_api
    def upload_resources(
        self, source: Union[IO, Path, str], path_in_zip: Union[Path, str] = ""
    ) -> List[str]:
        """
        Upload file to the pipeline resources. Existing files with same path/name will be overwritten.

        :return: List of resources after upload.
        """
        # noinspection PyProtectedMember
        zip_file = self.project.client._create_zip_io(source, path_in_zip)
        # noinspection PyProtectedMember
        return self.project.client._upload_resources(
            zip_file, project_name=self.project.name, pipeline_name=self.name
        )["files"]

    @experimental_api
    def download_resources(self, target_zip_path: Union[Path, str]) -> None:
        """
        Download pipeline resources and store in given path.
        """
        # noinspection PyProtectedMember
        self.project.client._download_resources(
            target_zip_path, project_name=self.project.name, pipeline_name=self.name
        )

    def collection_process_complete(self) -> dict:
        """
        Trigger collection process complete of the given pipeline.
        """
        # noinspection PyProtectedMember
        return self.project.client._collection_process_complete(self.project.name, self.name)


class Terminology:
    EXPORT_STATE_COMPLETED = "COMPLETED"
    EXPORT_STATE_PROCESSING_EXPORT = "PROCESSING_EXPORT"
    EXPORT_STATE_PREPARING = "PREPARING"
    EXPORT_STATE_ABORTING = "ABORTING"
    EXPORT_STATE_ABORTED = "ABORTED"
    EXPORT_STATE_FAILED = "FAILED"

    PENDING_EXPORT_STATES = [EXPORT_STATE_PROCESSING_EXPORT, EXPORT_STATE_PREPARING]

    IMPORT_STATE_PREPARING = "PREPARING"
    IMPORT_STATE_PROCESSING_CONCEPTS = "PROCESSING_CONCEPTS"
    IMPORT_STATE_PROCESSING_RELATIONS = "PROCESSING_RELATIONS"
    IMPORT_STATE_COMPLETED = "COMPLETED"
    IMPORT_STATE_ABORTING = "ABORTING"
    IMPORT_STATE_ABORTED = "ABORTED"
    IMPORT_STATE_FAILED = "FAILED"

    PENDING_IMPORT_STATES = [
        IMPORT_STATE_PREPARING,
        IMPORT_STATE_PROCESSING_CONCEPTS,
        IMPORT_STATE_PROCESSING_RELATIONS,
    ]

    def __init__(self, project: "Project", name: str):
        self.project = project
        self.name = name

    def __repr__(self):
        return f'{self.__class__.__name__}(name="{self.name}", project="{self.project.name}")'

    def start_export(self, terminology_format: str = TERMINOLOGY_EXPORTER_OBO_1_4) -> None:
        """
        Trigger the export of the terminology.
        """
        # noinspection PyProtectedMember
        self.project.client._start_terminology_export(
            self.project.name, self.name, terminology_format
        )

    def get_export_status(self) -> dict:
        """
        Obtain the status of the terminology export.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._get_terminology_export_info(self.project.name, self.name)

    def start_import(
        self, source: Union[IO, str], importer: str = TERMINOLOGY_IMPORTER_OBO
    ) -> None:
        """
        Upload the given terminology and trigger its import.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        self.project.client._start_terminology_import(
            self.project.name, self.name, importer, source
        )

    def get_import_status(self) -> dict:
        """
        Obtain the status of the import of the terminology.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._get_terminology_import_info(self.project.name, self.name)

    def import_data(
        self, source: Union[IO, str], importer: str = TERMINOLOGY_IMPORTER_OBO, timeout: int = 120
    ) -> dict:
        """
        Imports the given terminology into the platform and waits for the import process to complete. If the import
        does not complete successfully within the given period of time, an OperationTimeoutError is generated.
        """
        self.start_import(source, importer)
        started_at = time()
        while time() < started_at + timeout:
            status = self.get_import_status()
            if "state" in status and status["state"] == self.IMPORT_STATE_COMPLETED:
                return status
            elif "state" in status and status["state"] in self.PENDING_IMPORT_STATES:
                sleep(5)
            else:
                raise Exception(f"Terminology import failed: {status['state']}")

        raise OperationTimeoutError(
            f"Terminology import did not complete after {round(time() - started_at)} seconds"
        )

    def provision(self, timeout: int = 120) -> Optional[dict]:
        """
        Provisions the terminology so it can be used by pipelines. If the data cannot be successfully provisioned in
        the given period of time, an OperationTimeoutError is generated.
        """
        self.start_export(TERMINOLOGY_EXPORTER_CONCEPT_DICTIONARY_XML)
        started_at = time()
        while time() < started_at + timeout:
            status = self.get_export_status()
            if "state" in status and status["state"] == self.EXPORT_STATE_COMPLETED:
                return status
            elif "state" in status and status["state"] in self.PENDING_EXPORT_STATES:
                sleep(5)
            else:
                raise Exception(f"Terminology provisioning failed: {status['state']}")

        raise OperationTimeoutError(
            f"Terminology provisioning did not complete after {round(time() - started_at)} seconds"
        )

    def delete(self) -> None:
        """
        Delete the terminology.
        """
        # noinspection PyProtectedMember
        self.project.client._delete_terminology(self.project.name, self.name)


class Process:
    def __init__(
        self,
        project: "Project",
        name: str,
        document_source_name: str,
        pipeline_name: str,
        preceding_process_name=None,
    ):
        self.project = project
        self.name = name
        self.document_source_name = document_source_name
        self.pipeline_name = pipeline_name
        self.preceding_process_name = preceding_process_name

    def __repr__(self):
        return (
            f'{self.__class__.__name__}(name="{self.name}", project="{self.project.name}",'
            f' pipeline_name="{self.pipeline_name}", document_source_name="{self.document_source_name}",'
            f' preceding_process_name="{self.preceding_process_name}")'
        )

    class ProcessState:
        def __init__(
            self,
            *args,
            **kwargs,
        ):
            # TODO: We have a different set of parameters per platform version. Right now, all parameters are supported.
            #       When v6 is released, only the following subset should be kept.
            # process: "Process",
            # state: str,
            # number_of_total_documents: int,
            # number_of_successful_documents: int,
            # number_of_unsuccessful_documents: int,
            # error_messages: List[str],
            # preceding_process_name: str
            self.process: Process = kwargs.get("process")
            self.state: str = kwargs.get("state")
            self.processed_documents: int = kwargs.get("processed_documents")
            self.number_of_total_documents: int = kwargs.get("number_of_total_documents")
            self.number_of_successful_documents: int = kwargs.get("number_of_successful_documents")
            self.number_of_unsuccessful_documents: int = kwargs.get(
                "number_of_unsuccessful_documents"
            )
            self.error_messages: List[str] = kwargs.get("error_messages")

    @experimental_api
    def delete(self):
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Deletes the process as soon as it becomes IDLE. All document analysis results will be deleted.
        """
        # noinspection PyProtectedMember
        self.project.client._delete_process(self.project.name, self.name, self.document_source_name)

    @experimental_api
    def create_and_run_process(
        self, process_name: str, pipeline: Union[str, Pipeline]
    ) -> "Process":
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Creates a process upon the results of this process.
        """

        document_collection = self.project.get_document_collection(self.document_source_name)

        # noinspection PyProtectedMember
        self.project.client._create_and_run_process(
            document_collection=document_collection,
            process_name=process_name,
            pipeline=pipeline,
            preceding_process_name=self.name,
        )

        return document_collection.get_process(process_name=process_name)

    @experimental_api
    def rerun(self):
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Triggers a rerun if the process is IDLE.
        All current results will be deleted and the documents will be reprocessed.
        """
        # noinspection PyProtectedMember
        self.project.client._reprocess(self.project.name, self.name, self.document_source_name)

    @experimental_api
    def get_process_state(self) -> ProcessState:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Returns the current process state.
        """
        # noinspection PyProtectedMember
        return self.project.client._get_process_state(self.project, self)

    def export_text_analysis(self, annotation_types: str = None) -> dict:
        """
        Exports a given text analysis process as a json.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
         representation.
        """
        if self.project.client.get_spec_version().startswith("5."):
            raise OperationNotSupported(
                "Text analysis export is not supported for platform version 5.x, it is only supported from 6.x onwards."
            )

        # noinspection PyProtectedMember
        return self.project.client._export_text_analysis(
            self.project.name, self.document_source_name, self.name, annotation_types
        )

    @experimental_api
    def export_text_analysis_to_cas(self, document_id: str) -> Cas:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Returns an analysis as a UIMA CAS.
        """

        type_system = load_typesystem(
            self.project.client._export_analysis_result_typesystem(
                self.project.name, self.document_source_name, document_id, self
            )
        )

        # noinspection PyProtectedMember
        return load_cas_from_xmi(
            self.project.client._export_analysis_result_to_xmi(
                self.project.name, self.document_source_name, document_id, self
            ),
            typesystem=type_system,
        )


class DocumentCollection:
    def __init__(self, project: "Project", name: str):
        self.project = project
        self.name = name

    def __repr__(self):
        return f'{self.__class__.__name__}(name="{self.name}", project="{self.project.name}")'

    def get_number_of_documents(self) -> int:
        """
        Returns the number of documents in that collection.
        """
        # noinspection PyProtectedMember
        return self.project.client._get_document_collection(self.project.name, self.name)[
            "numberOfDocuments"
        ]

    @experimental_api
    def get_process(self, process_name: str) -> Process:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Get a process
        :return: The process
        """
        # noinspection PyProtectedMember
        return self.project.client._get_process(self, process_name)

    @experimental_api
    def create_and_run_process(
        self,
        process_name: str,
        pipeline: Union[str, Pipeline],
    ) -> Process:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Creates a process and runs the document analysis.
        :return: The created process
        """
        # noinspection PyProtectedMember
        self.project.client._create_and_run_process(self, process_name, pipeline)

        return self.get_process(process_name)

    def delete(self) -> dict:
        """
        Deletes the document collection.
        """
        # noinspection PyProtectedMember
        return self.project.client._delete_document_collection(self.project.name, self.name)

    def import_documents(
        self,
        source: Union[Cas, Path, IO, str],
        mime_type: str = None,
        filename: str = None,
        typesystem: "TypeSystem" = None,
    ) -> List[dict]:
        """
        Imports documents from a given file. Supported file content types are plain text (text/plain),
        Averbis Solr XML (application/vnd.averbis.solr+xml) and UIMA CAS XMI (application/vnd.uima.cas+xmi).

        If a document is provided as a CAS object, the type system information can be automatically picked from the CAS
        object and should not be provided explicitly. If a CAS is provided as a string XML representation, then a type
        system must be explicitly provided.

        The method tries to automatically determine the format (mime type) of the provided document, so setting the
        mime type parameter should usually not be necessary.

        If possible, the method obtains the file name from the provided source. If this is not possible (e.g. if the
        source is a string or a CAS object), the file name should explicitly be provided. If no filename is provided,
        a default filename is used. Note that a file in the Averbis Solr XML format can contain multiple documents
        and each of these has its name encoded within the XML. In this case, the setting filename parameter is not
        permitted at all.
        """

        # noinspection PyProtectedMember
        return self.project.client._import_documents(
            self.project.name, self.name, source, mime_type, filename, typesystem
        )

    @experimental_api
    def list_documents(self) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Lists the documents in the collection.
        """
        # noinspection PyProtectedMember
        return self.project.client._list_documents(self.project.name, self.name)

    @experimental_api
    def list_processes(self) -> List[Process]:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Lists the processes of the collection.
        """
        return [
            process
            for process in self.project.list_processes()
            if process.document_source_name == self.name
        ]


class Pear:
    def __init__(self, project: "Project", identifier: str):
        self.project = project
        self.identifier = identifier

    def __repr__(self):
        return f'{self.__class__.__name__}(identifier="{self.identifier}", project="{self.project.name}")'

    @experimental_api
    def delete(self):
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Deletes the PEAR.
        """
        # noinspection PyProtectedMember
        self.project.client._delete_pear(self.project.name, self.identifier)

    @experimental_api
    def get_default_configuration(self) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Get the default configuration of the PEAR.
        """
        # noinspection PyProtectedMember
        return self.project.client._get_default_pear_configuration(
            self.project.name, self.identifier
        )


class Project:
    def __init__(self, client: "Client", name: str):
        self.client = client
        self.name = name
        self.__cached_pipelines: dict = {}

    def __repr__(self):
        return f'{self.__class__.__name__}(name="{self.name}")'

    def get_pipeline(self, name: str) -> Pipeline:
        """
        Access an existing pipeline.

        :return: The pipeline.
        """
        if name not in self.__cached_pipelines:
            self.__cached_pipelines[name] = Pipeline(self, name)

        return self.__cached_pipelines[name]

    def create_pipeline(self, configuration: dict, name: str = None) -> Pipeline:
        """
        Create a new pipeline.

        :return: The pipeline.
        """

        # The pipeline name parameter differs between schemaVersion 1.x ("name") and 2.x ("pipelineName")
        if configuration["schemaVersion"].startswith("1."):
            pipeline_name_key = "name"
        else:
            pipeline_name_key = "pipelineName"

        if name is not None:
            cfg = copy.deepcopy(configuration)
            cfg[pipeline_name_key] = name
        else:
            cfg = configuration
            name = cfg[pipeline_name_key]

        # noinspection PyProtectedMember
        self.client._create_pipeline(self.name, cfg)
        new_pipeline = Pipeline(self, name)
        self.__cached_pipelines[name] = new_pipeline
        return new_pipeline

    @experimental_api
    def list_pipelines(self) -> List[Pipeline]:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        List pipelines for the current project.

        :return: List of pipelines.
        """
        response = self.client._list_pipelines(self.name)

        return [Pipeline(self, p["name"]) for p in response]

    @experimental_api
    def exists_pipeline(self, name: str) -> bool:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Checks if a pipeline exists.
        """

        pipelines = self.list_pipelines()
        return any(p.name == name for p in pipelines)

    def create_terminology(
        self,
        terminology_name: str,
        label: str,
        languages: List[str],
        concept_type: str = "de.averbis.extraction.types.Concept",
        version: str = "",
        hierarchical: bool = True,
    ) -> Terminology:
        """
        Create a new terminology.

        :return: The terminology.
        """
        # noinspection PyProtectedMember
        response = self.client._create_terminology(
            self.name, terminology_name, label, languages, concept_type, version, hierarchical
        )
        return Terminology(self, response["terminologyName"])

    def get_terminology(self, terminology: str) -> Terminology:
        """
        Obtain an existing terminology.

        :return: The terminology.
        """
        return Terminology(self, terminology)

    def list_terminologies(self) -> dict:
        """
        List all existing terminologies.

        :return: The terminology list.
        """
        # noinspection PyProtectedMember
        return self.client._list_terminologies(self.name)

    def create_document_collection(self, name: str) -> DocumentCollection:
        """
        Creates a new document collection.

        :return: The document collection.
        """
        # noinspection PyProtectedMember
        return self.client._create_document_collection(self.name, name)

    def get_document_collection(self, collection: str) -> DocumentCollection:
        """
        Obtain an existing document collection.

        :return: The document collection.
        """
        # noinspection PyProtectedMember
        return DocumentCollection(self, collection)

    def list_document_collections(self) -> List[DocumentCollection]:
        """
        Lists all document collections.

        :return: List of DocumentCollection objects
        """
        # noinspection PyProtectedMember
        collections = self.client._list_document_collections(self.name)
        return [DocumentCollection(self, c["name"]) for c in collections]

    def exists_document_collection(self, name: str):
        """
        Checks if a document collection exists.

        :return: Whether the collection exists
        """
        # noinspection PyProtectedMember
        collections = self.client._list_document_collections(self.name)
        return any(c["name"] == name for c in collections)

    def delete(self) -> None:
        """
        Delete the project.
        """
        # noinspection PyProtectedMember
        self.client._delete_project(self.name)
        return None

    def classify_text(self, text: str, classification_set: str = "Default") -> dict:
        """
        Classify the given text.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.client._classify_document(
            self.name, text.encode(ENCODING_UTF_8), classification_set, DOCUMENT_IMPORTER_TEXT
        )

    def search(self, query: str = "", **kwargs) -> dict:
        """
        Search for documents matching the query.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.client._select(self.name, query, **kwargs)

    @experimental_api
    def list_pears(self) -> List[str]:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        List all existing pears by identifier.
        :return: The list of pear identifiers.
        """
        # noinspection PyProtectedMember
        return self.client._list_pears(self.name)

    @experimental_api
    def delete_pear(self, pear_identifier: str) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Delete the pear by identifier.
        """
        # noinspection PyProtectedMember
        return self.client._delete_pear(self.name, pear_identifier)

    @experimental_api
    def install_pear(self, file_or_path: Union[IO, Path, str]) -> Pear:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Install a pear by file or path.
        """
        # noinspection PyProtectedMember
        pear_identifier = self.client._install_pear(self.name, file_or_path)
        return Pear(self, pear_identifier)

    @experimental_api
    def list_processes(self) -> List[Process]:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        List all existing processes by name and document source name.
        :return: The list of processes.
        """
        # noinspection PyProtectedMember
        return self.client._list_processes(self)

    @experimental_api
    def list_resources(self) -> List[str]:
        """
        List the resources of the project.

        :return: The list of project resources.
        """
        # noinspection PyProtectedMember
        return self.client._list_resources(project_name=self.name)["files"]

    @experimental_api
    def download_resources(self, target_zip_path: Union[Path, str]) -> None:
        """
        Download Project-level pipeline resources and store in given path.
        """
        # noinspection PyProtectedMember
        self.client._download_resources(target_zip_path, project_name=self.name)

    @experimental_api
    def delete_resources(self) -> None:
        """
        Delete the resources of the project.
        """
        # noinspection PyProtectedMember
        self.client._delete_resources(project_name=self.name)

    @experimental_api
    def upload_resources(
        self, source: Union[IO, Path, str], path_in_zip: Union[Path, str] = ""
    ) -> List[str]:
        """
        Upload file to the project resources. Existing files with same path/name will be overwritten.

        :return: List of resources after upload.
        """
        # noinspection PyProtectedMember
        zip_file = self.client._create_zip_io(source, path_in_zip)
        # noinspection PyProtectedMember
        return self.client._upload_resources(zip_file, project_name=self.name)["files"]


class Client:
    def __init__(
        self,
        url_or_id: str,
        api_token: str = None,
        verify_ssl: Union[str, bool] = True,
        settings: Union[str, Path, dict] = None,
        username: str = None,
        password: str = None,
        timeout: float = None,
    ):
        """
        A Client is the base object for all calls within the Averbis Python API.

        The Client can be initialized by passing the required parameters (e.g. URL and API Token) or
        by creating a client-settings.json file in which the information is stored.
        The client-settings.json allows specifying different profiles for different servers.
        Please see the example in the project README for more information.

        :param url_or_id:  The URL to the platform instance or an identifier of a profile in a client settings file
        :param api_token:  The API Token enabling users to perform requests in the platform
        :param verify_ssl: Whether the SSL verifcation should be activated (default=True)
        :param settings:   Either a dictionary containing settings information or a path to the settings file.
                           As fallback, a "client-settings.json" file is searched in the current directory and in $HOME/.averbis/
        :param username:   If no API token is provided, then a username can be provided together with a password to generate a new API token
        :param password:   If no API token is provided, then a username can be provided together with a password to generate a new API token
        :param timeout:    An optional global timeout (in seconds) specifiying how long the Client is waiting for a server response (default=None).
        """

        self.__logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
        self._api_token = api_token
        self._verify_ssl = verify_ssl
        self._timeout = timeout

        if isinstance(settings, dict):
            self._settings = settings
        else:
            self._settings = self._load_settings(settings)

        if url_or_id.lower().startswith("http://") or url_or_id.lower().startswith("https://"):
            self._url = url_or_id
        else:
            if self._exists_profile("*"):
                self._apply_profile("*")
            self._apply_profile(url_or_id)

        if self._api_token is None:
            if username is not None and password is not None:
                self.regenerate_api_token(username, password)
            else:
                raise Exception(
                    "An API Token is required for initializing the Client.\n"
                    + "You can either pass it directly with: Client(url,api_token=your_token) or you can\n"
                    + "generate a new API token with: Client(url, username='your_user_name', password='your_password')."
                )
        self._build_info: dict = {}
        self._spec_version: str = ""

    def __repr__(self):
        return f"{self.__class__.__name__}({self._url})"

    def _exists_profile(self, profile: str):
        return (
            self._settings
            and "profiles" in self._settings
            and profile in self._settings["profiles"]
        )

    def _apply_profile(self, profile: str):
        if not self._exists_profile(profile):
            raise Exception(f"No profile named {profile} found in settings")

        connection_profile = self._settings["profiles"][profile]

        if "url" in connection_profile:
            self._url = connection_profile["url"]
        if "api-token" in connection_profile:
            self._api_token = connection_profile["api-token"]
        if "verify-ssl" in connection_profile:
            self._verify_ssl = connection_profile["verify-ssl"]
        if "timeout" in connection_profile:
            self._timeout = connection_profile["timeout"]

    def _load_settings(self, path: Union[str, Path] = None) -> dict:
        """
        Loads the client settings from a given path or (as fallback) searches for a "client-settings.json" file in the current path or in $HOME/.averbis.

        :param path: Direct path to the settings json file (optional)
        :return: A dictionary containing information about the client (URL, API Token, etc.).
        """
        if path:
            path = path if isinstance(path, Path) else Path(path)
            self.__logger.info(f"Loading settings from {path}")
            with path.open(encoding=ENCODING_UTF_8) as source:
                return json.load(source)

        cwd_settings_path = Path.cwd().joinpath("client-settings.json")
        if cwd_settings_path.exists():
            self.__logger.info(f"Loading settings from {cwd_settings_path}")
            with cwd_settings_path.open(encoding=ENCODING_UTF_8) as source:
                return json.load(source)

        per_user_settings_path = Path.home().joinpath(".averbis/client-settings.json")
        if per_user_settings_path.exists():
            self.__logger.info(f"Loading settings from {per_user_settings_path}")
            with per_user_settings_path.open(encoding=ENCODING_UTF_8) as source:
                return json.load(source)

        return {}

    def set_timeout(self, timeout: float) -> "Client":
        """
        Overwriting the Client-level timeout with a new timeout.

        :param timeout: Timeout duration in seconds
        :return: The client.
        """
        self._timeout = timeout
        return self

    def ensure_available(self, timeout: float = 120) -> "Client":
        """
        Checks whether the server is available and responding. The call will block for a given time if the server
        is not available. If the time has passed without the server becoming available , an exception will be generated.
        """
        started_at = time()
        while time() < started_at + timeout:
            try:
                response = requests.get(self._url, timeout=2, verify=self._verify_ssl)
                if response.ok:
                    return self
                self.__logger.info(
                    "Server responded %s: waiting for server to become available...",
                    response.status_code,
                )
            except requests.RequestException as e:
                self.__logger.info(
                    "Server connection failed: waiting for server to become available..."
                )
                pass
            sleep(5)

        raise OperationTimeoutError(
            f"Server still not available after {round(time() - started_at)} seconds"
        )

    def _run_request(self, method: str, endpoint: str, **kwargs) -> requests.Response:
        def make_value_compatible_with_rest_api(value):
            if value is True:
                return "true"
            elif value is False:
                return "false"
            else:
                return value

        if "headers" in kwargs:
            kwargs["headers"] = self._default_headers(kwargs.get("headers"))
        else:
            kwargs["headers"] = self._default_headers()

        if "json" in kwargs:
            kwargs["headers"][HEADER_CONTENT_TYPE] = MEDIA_TYPE_APPLICATION_JSON

        if "params" in kwargs:
            kwargs["params"] = {
                k: make_value_compatible_with_rest_api(v) for k, v in kwargs["params"].items()
            }

        kwargs["verify"] = self._verify_ssl

        if "timeout" not in kwargs or kwargs["timeout"] is None:
            kwargs["timeout"] = self._timeout

        url = self._build_url(endpoint)
        raw_response = requests.request(method, url, **kwargs)
        self.__logger.debug(
            "Response for %s %s: %s -- %s", method, url, raw_response, raw_response.content
        )
        return raw_response

    def _build_url(self, endpoint):
        return f"{self._url.rstrip('/')}/rest/{endpoint.lstrip('/')}"

    def __request_with_json_response(self, method: str, endpoint: str, **kwargs) -> dict:
        """
        A json response is used in almost all endpoints. Error messages are also returned as json.
        """
        raw_response = self._run_request(method, endpoint, **kwargs)

        if not raw_response.ok:
            self.__handle_error(raw_response)

        try:
            return raw_response.json()
        except JSONDecodeError as e:
            raise JSONDecodeError(
                msg="The server successfully returned a response, however, this response could not be converted to Json.",
                doc=e.doc,
                pos=e.pos,
            )

    def __request_with_bytes_response(self, method: str, endpoint: str, **kwargs) -> bytes:
        """
        A bytes response is used in the experimental API for encoding CAS objects.
        """
        raw_response = self._run_request(method, endpoint, **kwargs)
        if not raw_response.ok:
            self.__handle_error(raw_response)

        content_type_header = raw_response.headers.get(HEADER_CONTENT_TYPE, "")
        is_actually_json_response = MEDIA_TYPE_APPLICATION_JSON in content_type_header
        if is_actually_json_response:
            raise TypeError(
                f"Expected the return content to be bytes, but got [{content_type_header}]: {raw_response}"
            )
        return raw_response.content

    def _default_headers(self, items=None) -> dict:
        if items is None:
            items = {}

        headers = {
            HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_JSON,
            **items,
        }

        if self._api_token:
            headers["api-token"] = self._api_token

        return headers

    def change_password(self, user: str, old_password: str, new_password: str) -> dict:
        """
        Changes the password of the given user.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        response = self.__request_with_json_response(
            "put",
            f"/v1/users/{user}/changeMyPassword",
            json={"oldPassword": old_password, "newPassword": new_password},
        )
        return response["payload"]

    def generate_api_token(self, user: str, password: str) -> Optional[str]:
        """
        Generates an API token using the given user/password and stores the API token in the client for further use.
        Normally, you would never call this method but rather work with a previously generated API token.

        :return: the API token that was obtained
        """

        response = self.__request_with_json_response(
            "post", f"/v1/users/{user}/apitoken", json={"password": password, "userSourceName": ""}
        )
        self._api_token = response["payload"]
        return self._api_token

    def regenerate_api_token(self, user: str, password: str) -> Optional[str]:
        """
        Regenerates an API token using the given user/password and stores the API token in the client for further use.
        Normally, you would never call this method but rather work with a previously generated API token.

        :return: the API token that was obtained
        """

        response = self.__request_with_json_response(
            "put", f"/v1/users/{user}/apitoken", json={"password": password, "userSourceName": ""}
        )
        self._api_token = response["payload"]
        return self._api_token

    def invalidate_api_token(self, user: str, password: str) -> None:
        """
        Invalidates the API token for the given user. This method does not clear the API token from this client object.
        If the client is currently using the API token that is being cleared, subsequent operations will fail.
        """
        self.__request_with_json_response(
            "delete",
            f"/v1/users/{user}/apitoken",
            json={"password": password, "userSourceName": ""},
        )
        return None

    def get_api_token_status(self, user: str, password: str) -> str:
        """
        Obtains the status of the given API token.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        response = self.__request_with_json_response(
            "post",
            f"/v1/users/{user}/apitoken/status",
            json={"password": password, "userSourceName": ""},
        )
        return response["payload"]

    def get_spec_version(self) -> str:
        """
        Helper function that returns the spec version of the server instance.

        :return: The spec version as string
        """
        return self.get_build_info()["specVersion"]

    def get_build_info(self) -> dict:
        """
        Obtains information about the version of the server instance.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        if not self._build_info:
            response = self.__request_with_json_response("get", f"/v1/buildInfo")
            self._build_info = response["payload"]
        return self._build_info

    def create_project(self, name: str, description: str = "") -> Project:
        """
        Creates a new project.

        :return: The project.
        """
        response = self.__request_with_json_response(
            "post", f"/v1/projects", params={"name": name, "description": description}
        )
        return Project(self, response["payload"]["name"])

    def get_project(self, name: str) -> Project:
        """
        Access an existing project.

        :return: The project.
        """
        return Project(self, name)

    @experimental_api
    def list_resources(self) -> List[str]:
        """
        List the resources that are globally available.

        :return: List of resources.
        """
        return self._list_resources()["files"]

    @experimental_api
    def download_resources(self, target_zip_path: Union[Path, str]) -> None:
        """
        Download Client-level pipeline resources and store in given path.
        """
        # noinspection PyProtectedMember
        self._download_resources(target_zip_path)

    @experimental_api
    def delete_resources(self) -> None:
        """
        Delete the global resources.
        """
        # noinspection PyProtectedMember
        self._delete_resources()

    @experimental_api
    def upload_resources(
        self, source: Union[IO, Path, str], path_in_zip: Union[Path, str] = ""
    ) -> List[str]:
        """
        Upload file to the global resources. Existing files with same path/name will be overwritten.

        :return: List of resources after upload.
        """
        zip_file = self._create_zip_io(source, path_in_zip)
        return self._upload_resources(zip_file)["files"]

    @experimental_api
    def list_projects(self) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Returns a list of the projects.
        """

        response = self.__request_with_json_response("get", f"/experimental/projects")
        return response["payload"]

    @experimental_api
    def exists_project(self, name: str) -> bool:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Checks if a project exists.
        """

        projects = self.list_projects()
        return any(p["name"] == name for p in projects)

    @experimental_api
    def _delete_project(self, name: str) -> None:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Project.delete() instead.
        """
        if self.get_build_info()["specVersion"].startswith("5."):
            raise OperationNotSupported(
                "Deleting projects is not supported in platform version 5.x."
            )

        response = self.__request_with_json_response("delete", f"/experimental/projects/{name}")
        return response["payload"]

    def _list_document_collections(self, project: str) -> dict:
        """
        Use Project.list_document_collections() instead.
        """
        response = self.__request_with_json_response(
            "get", f"/v1/importer/projects/{project}/documentCollections"
        )

        return response["payload"]

    def _create_document_collection(self, project: str, collection_name: str) -> DocumentCollection:
        """
        Use Project.create_document_collection() instead.
        """
        response = self.__request_with_json_response(
            "post",
            f"/v1/importer/projects/{project}/documentCollections",
            json={"name": collection_name},
        )
        return DocumentCollection(self.get_project(project), response["payload"]["name"])

    def _get_document_collection(self, project: str, collection_name: str):
        """
        Use DocumentCollection.get_number_of_documents() instead.
        """
        response = self.__request_with_json_response(
            "get", f"/v1/importer/projects/{project}/documentCollections/{collection_name}"
        )

        return response["payload"]

    def _delete_document_collection(self, project: str, collection_name: str) -> dict:
        """
        Use DocumentCollection.delete() instead.
        """
        response = self.__request_with_json_response(
            "delete", f"/v1/importer/projects/{project}/documentCollections/{collection_name}"
        )
        return response["payload"]

    @experimental_api
    def _list_documents(self, project: str, collection_name: str) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Lists the documents in the collection.
        """

        response = self.__request_with_json_response(
            "get",
            f"/experimental/projects/{project}/documentCollections/{collection_name}/documents",
        )
        return response["payload"]

    def _import_documents(
        self,
        project: str,
        collection_name: str,
        source: Union[Cas, Path, IO, str],
        mime_type: str = None,
        filename: str = None,
        typesystem: "TypeSystem" = None,
    ) -> List[dict]:
        """
        Use DocumentCollection.import_document() instead.
        """

        def fetch_filename(src: Union[Path, IO, str], default_filename: str) -> str:
            if isinstance(src, Path):
                return Path(src).name

            if isinstance(src, IOBase) and hasattr(src, "name"):
                return src.name

            if isinstance(src, str):
                return default_filename

            raise ValueError("Unsupported source type - valid is [Path, IO, str]")

        if isinstance(source, str) and mime_type is None:
            mime_type = MEDIA_TYPE_TEXT_PLAIN

        if isinstance(source, Cas):
            if (mime_type is not None) and (mime_type != MEDIA_TYPE_APPLICATION_XMI):
                raise Exception(
                    f"The format {mime_type} is not supported for CAS objects. It must be set to "
                    f"{MEDIA_TYPE_APPLICATION_XMI} or be omitted."
                )
            mime_type = MEDIA_TYPE_APPLICATION_XMI

        # If the format is not a multi-document format, we need to have a filename. If it is a multi-document
        # format, then the server is using the filenames stored within the multi-document
        if mime_type in [MEDIA_TYPE_APPLICATION_SOLR_XML]:
            if filename is not None:
                raise Exception(
                    f"The filename parameter cannot be used in conjunction with multi-document file formats "
                    f"such as {mime_type}"
                )
            # For multi-documents, the server still needs a filename with the proper extension, otherwise it refuses
            # to parse the result
            filename = fetch_filename(source, "data.xml")
        else:
            filename = filename or fetch_filename(source, "document.txt")

            if mime_type is None:
                # Inferring MimeType if not set
                mime_type = mimetypes.guess_type(url=filename)[0]
                if mime_type not in [MEDIA_TYPE_TEXT_PLAIN, MEDIA_TYPE_APPLICATION_SOLR_XML]:
                    raise ValueError(
                        f"Unable to guess a valid mime_type. Supported file content types are plain text (mime_type = "
                        f"'{MEDIA_TYPE_TEXT_PLAIN}') and Averbis Solr XML (mime_type = "
                        f"'{MEDIA_TYPE_APPLICATION_SOLR_XML}').\n"
                        f"Please provide the correct mime_type with: `document_collection.import_documents(file, "
                        f"mime_type = ...)`."
                    )

        if isinstance(source, Path):
            if mime_type == MEDIA_TYPE_TEXT_PLAIN:
                with source.open("r", encoding=ENCODING_UTF_8) as text_file:
                    source = text_file.read()
            else:
                with source.open("rb") as binary_file:
                    source = BytesIO(binary_file.read())

        if isinstance(source, Cas):
            if typesystem is None:
                typesystem = source.typesystem
            source = source.to_xmi()

        data: IO = BytesIO(source.encode(ENCODING_UTF_8)) if isinstance(source, str) else source

        files = {"documentFile": (filename, data, mime_type)}
        if typesystem:
            files["typesystemFile"] = (
                "typesystem.xml",
                typesystem.to_xml(),
                MEDIA_TYPE_APPLICATION_XML,
            )

        response = self.__request_with_json_response(
            "post",
            f"/v1/importer/projects/{project}/documentCollections/{collection_name}/documents",
            files=files,
        )

        # When a multi-document file format is uploaded (e.g. SolrXML), we get an array as a result, otherwise we get
        # an object. To have a uniform API we wrap the object in an array so we always get an array as a result.
        if isinstance(response["payload"], list):
            return response["payload"]
        else:
            return [response["payload"]]

    def _list_terminologies(self, project: str) -> dict:
        """
        Use Project.list_terminologies() instead.
        """
        response = self.__request_with_json_response(
            "get", f"/v1/terminology/projects/{project}/terminologies"
        )
        return response["payload"]

    def _create_terminology(
        self,
        project: str,
        terminology: str,
        label: str,
        languages: List[str],
        concept_type: str = "de.averbis.extraction.types.Concept",
        version: str = "",
        hierarchical: bool = True,
    ) -> dict:
        """
        Use Project.create_terminology() instead.
        """
        response = self.__request_with_json_response(
            "post",
            f"/v1/terminology/projects/{project}/terminologies",
            json={
                "terminologyName": terminology,
                "label": label,
                "conceptType": concept_type,
                "version": version,
                "hierarchical": hierarchical,
                "allowedLanguageCodes": languages,
            },
        )
        return response["payload"]

    def _delete_terminology(self, project: str, terminology: str) -> None:
        """
        Use Terminology.delete() instead.
        """
        self.__request_with_json_response(
            "delete", f"/v1/terminology/projects/{project}/terminologies/{terminology}"
        )

    def _start_terminology_export(self, project: str, terminology: str, exporter: str) -> None:
        """
        Use Terminology.start_export() instead.
        """
        self.__request_with_json_response(
            "post",
            f"/v1/terminology/projects/{project}/terminologies/{terminology}/terminologyExports",
            params={"terminologyExporterName": exporter},
        )

    def _get_terminology_export_info(self, project: str, terminology: str) -> dict:
        """
        Use Terminology.get_export_status() instead.
        """
        response = self.__request_with_json_response(
            "get",
            f"/v1/terminology/projects/{project}/terminologies/{terminology}/terminologyExports",
        )
        return response["payload"]

    def _start_terminology_import(
        self, project: str, terminology: str, importer: str, source: Union[IO, str]
    ) -> None:
        """
        Use Terminology.start_import() instead.
        """

        def get_media_type_for_format() -> str:
            if importer == TERMINOLOGY_IMPORTER_OBO:
                return MEDIA_TYPE_TEXT_PLAIN_UTF8
            else:
                return MEDIA_TYPE_OCTET_STREAM

        data: IO = BytesIO(source.encode(ENCODING_UTF_8)) if isinstance(source, str) else source

        self.__request_with_json_response(
            "post",
            f"/v1/terminology/projects/{project}/terminologies/{terminology}/terminologyImports",
            data=data,
            params={"terminologyImportImporterName": importer},
            headers={HEADER_CONTENT_TYPE: get_media_type_for_format()},
        )

    def _get_terminology_import_info(self, project: str, terminology: str):
        """
        Use Terminology.get_import_status() instead.
        """
        response = self.__request_with_json_response(
            "get",
            f"/v1/terminology/projects/{project}/terminologies/{terminology}/terminologyImports",
            headers={HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_JSON},
        )
        return response["payload"]

    def _create_pipeline(self, project: str, configuration: dict) -> Pipeline:
        response = self.__request_with_json_response(
            "post",
            f"/v1/textanalysis/projects/{project}/pipelines",
            json=configuration,
        )
        return response["payload"]

    @experimental_api
    def _delete_pipeline(self, project: str, pipeline: str) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Pipeline.delete() instead.
        """
        response = self.__request_with_json_response(
            "delete", f"/experimental/textanalysis/projects/{project}/pipelines/{pipeline}"
        )
        return response["payload"]

    def _list_pipelines(self, project: str) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Project.list_pipelines() instead.
        """
        if self.get_spec_version().startswith("5."):
            raise OperationNotSupported(
                "Listing pipelines is not supported by the REST API in platform version 5.x, but only from 6.x "
                "onwards."
            )

        response = self.__request_with_json_response(
            "get", f"/experimental/textanalysis/projects/{project}/pipelines"
        )
        return response["payload"]

    def _start_pipeline(self, project: str, pipeline: str) -> dict:
        response = self.__request_with_json_response(
            "put", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/start"
        )
        return response["payload"]

    def _stop_pipeline(self, project: str, pipeline: str) -> dict:
        response = self.__request_with_json_response(
            "put", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/stop"
        )
        return response["payload"]

    def _get_pipeline_info(self, project: str, pipeline: str) -> dict:
        response = self.__request_with_json_response(
            "get", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}"
        )
        return response["payload"]

    def _get_pipeline_configuration(self, project: str, pipeline: str) -> dict:
        response = self.__request_with_json_response(
            "get", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/configuration"
        )
        return response["payload"]

    def _set_pipeline_configuration(self, project: str, pipeline: str, configuration: dict) -> None:
        self.__request_with_json_response(
            "put",
            f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/configuration",
            json=configuration,
        )

    def _classify_document(
        self,
        project: str,
        data,
        classification_set: str = "Default",
        data_format=DOCUMENT_IMPORTER_TEXT,
        timeout: float = None,
    ) -> dict:
        def get_media_type_for_format() -> str:
            if data_format == DOCUMENT_IMPORTER_TEXT:
                return MEDIA_TYPE_TEXT_PLAIN_UTF8
            else:
                return MEDIA_TYPE_OCTET_STREAM

        response = self.__request_with_json_response(
            "post",
            f"/v1/classification/projects/{project}/classificationSets/{classification_set}/classifyDocument",
            data=data,
            params={"type": data_format},
            headers={HEADER_CONTENT_TYPE: get_media_type_for_format()},
            timeout=timeout,
        )
        return response["payload"]

    def _analyse_text(
        self,
        project: str,
        pipeline: str,
        source: Union[Path, IO, str],
        annotation_types: str = None,
        language: str = None,
        timeout: float = None,
    ) -> dict:
        if isinstance(source, Path):
            with source.open("r", encoding=ENCODING_UTF_8) as file:
                source = file.read()

        data: IO = BytesIO(source.encode(ENCODING_UTF_8)) if isinstance(source, str) else source

        response = self.__request_with_json_response(
            "post",
            f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/analyseText",
            data=data,
            params={"annotationTypes": annotation_types, "language": language},
            headers={HEADER_CONTENT_TYPE: MEDIA_TYPE_TEXT_PLAIN_UTF8},
            timeout=timeout,
        )
        return response["payload"]

    def _analyse_html(
        self,
        project: str,
        pipeline: str,
        source: Union[Path, IO, str],
        annotation_types: str = None,
        language: str = None,
        timeout: float = None,
    ) -> dict:
        if isinstance(source, Path):
            with source.open("r", encoding=ENCODING_UTF_8) as file:
                source = file.read()

        data: IO = BytesIO(source.encode(ENCODING_UTF_8)) if isinstance(source, str) else source

        response = self.__request_with_json_response(
            "post",
            f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/analyseHtml",
            data=data,
            params={"annotationTypes": annotation_types, "language": language},
            headers={HEADER_CONTENT_TYPE: MEDIA_TYPE_TEXT_PLAIN_UTF8},
            timeout=timeout,
        )
        return response["payload"]

    def _select(self, project: str, q: str = None, **kwargs) -> dict:
        response = self.__request_with_json_response(
            "get",
            f"/v1/search/projects/{project}/select",
            params={"q": q, **kwargs},
            headers={HEADER_CONTENT_TYPE: MEDIA_TYPE_TEXT_PLAIN_UTF8},
        )
        return response["payload"]

    def _export_text_analysis(
        self, project: str, document_source: str, process: str, annotation_types: str = None
    ):
        """
        Use Process.export_text_analysis() instead.
        """
        response = self.__request_with_json_response(
            "get",
            f"/v1/textanalysis/projects/{project}/documentSources/{document_source}/processes/{process}/export",
            params={"annotationTypes": annotation_types},
            headers={HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_JSON},
        )
        return response["payload"]

    @experimental_api
    def _export_analysis_result_to_xmi(
        self, project: str, collection_name: str, document_id: str, process: Union[Process, str]
    ) -> str:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Process.export_text_analysis_to_cas() instead.
        """

        if self.get_build_info()["specVersion"].startswith("5."):
            raise OperationNotSupported(
                "Text analysis export is not supported for platform version 5.x, it is only supported from 6.x onwards."
            )

        process_name = self.__process_name(process)

        return str(
            self.__request_with_bytes_response(
                "get",
                f"/experimental/textanalysis/projects/{project}/documentCollections/{collection_name}"
                f"/documents/{document_id}/processes/{process_name}/exportTextAnalysisResult",
                headers={
                    HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_XMI,
                },
            ),
            ENCODING_UTF_8,
        )

    @experimental_api
    def _export_analysis_result_typesystem(
        self, project: str, collection_name: str, document_id: str, process: Union[Process, str]
    ) -> str:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.
        """

        if self.get_build_info()["specVersion"].startswith("5."):
            raise OperationNotSupported(
                "Text analysis export is not supported for platform version 5.x, it is only supported from 6.x onwards."
            )

        process_name = self.__process_name(process)

        return str(
            self.__request_with_bytes_response(
                "get",
                f"/experimental/textanalysis/projects/{project}/documentCollections/{collection_name}"
                f"/documents/{document_id}/processes/{process_name}/exportTextAnalysisResultTypeSystem",
                headers={HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_XML},
            ),
            ENCODING_UTF_8,
        )

    @experimental_api
    def _analyse_text_xmi(
        self,
        project: str,
        pipeline: str,
        source: Union[IO, str],
        annotation_types: str = None,
        language: str = None,
        timeout: float = None,
    ) -> str:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Pipeline.analyse_text_to_cas() instead.
        """

        data: IO = BytesIO(source.encode(ENCODING_UTF_8)) if isinstance(source, str) else source

        return str(
            self.__request_with_bytes_response(
                "post",
                f"/experimental/textanalysis/projects/{project}/pipelines/{pipeline}/analyzeTextToCas",
                data=data,
                params={"annotationTypes": annotation_types, "language": language},
                headers={
                    HEADER_CONTENT_TYPE: MEDIA_TYPE_TEXT_PLAIN_UTF8,
                    HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_XMI,
                },
                timeout=timeout,
            ),
            ENCODING_UTF_8,
        )

    @experimental_api
    def _collection_process_complete(self, project: str, pipeline: str) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Pipeline.collection_process_complete() instead.
        """
        response = self.__request_with_json_response(
            "post",
            f"/experimental/textanalysis/projects/{project}/pipelines/{pipeline}/collectionProcessComplete",
        )

        return response["payload"]

    @experimental_api
    def _get_pipeline_type_system(self, project: str, pipeline: str) -> str:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Pipeline.get_type_system() instead.
        """

        return str(
            self.__request_with_bytes_response(
                "get",
                f"/experimental/textanalysis/projects/{project}/pipelines/{pipeline}/exportTypesystem",
                params={"annotationTypes": "*"},
                headers={HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_XML},
            ),
            ENCODING_UTF_8,
        )

    @experimental_api
    def _list_pears(self, project: str) -> List[str]:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Project.list_pears() instead.
        """
        response = self.__request_with_json_response(
            "get", f"/experimental/textanalysis/projects/{project}/pearComponents"
        )

        return response["payload"]

    @experimental_api
    def _delete_pear(self, project: str, pear_identifier: str) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Project.delete_pear() instead.
        """
        response = self.__request_with_json_response(
            "delete",
            f"/experimental/textanalysis/projects/{project}/pearComponents/{pear_identifier}",
        )

        return response["payload"]

    @experimental_api
    def _install_pear(self, project: str, file_or_path: Union[IO, Path, str]) -> str:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Project.install_pear() instead.
        """

        if isinstance(file_or_path, str):
            file_or_path = Path(file_or_path)
        if isinstance(file_or_path, Path):
            file_or_path = open(file_or_path, "rb")

        if not file_or_path.name.endswith(".pear"):
            raise Exception(f"{file_or_path.name} was not of type '.pear'")

        response = self.__request_with_json_response(
            "post",
            f"/experimental/textanalysis/projects/{project}/pearComponents",
            files={"pearPackage": (file_or_path.name, file_or_path, "application/octet-stream")},
        )

        return response["payload"][0]

    @experimental_api
    def _get_default_pear_configuration(self, project: str, pear_identifier: str) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Pear.get_default_configuration() instead.
        """
        response = self.__request_with_json_response(
            "get", f"/experimental/textanalysis/projects/{project}/pearComponents/{pear_identifier}"
        )

        return response["payload"]

    @experimental_api
    def _list_processes(self, project: "Project") -> List[Process]:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Project.list_processes() instead.
        """
        response = self.__request_with_json_response(
            "get", f"/experimental/textanalysis/projects/{project.name}/processes"
        )
        processes = []
        for item in response["payload"]:
            document_collection = project.get_document_collection(item["documentSourceName"])
            processes.append(document_collection.get_process(item["processName"]))
        return processes

    @experimental_api
    def _create_and_run_process(
        self,
        document_collection: DocumentCollection,
        process_name: str,
        pipeline: Union[str, Pipeline],
        preceding_process_name=None,
    ) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use DocumentCollection.create_and_run_process() instead.
        """
        pipeline_name = self.__pipeline_name(pipeline)

        project = document_collection.project

        request_json = {
            "processName": process_name,
            "documentSourceName": document_collection.name,
            "pipelineName": pipeline_name,
        }

        if preceding_process_name:
            request_json["precedingProcessName"] = preceding_process_name

        response = self.__request_with_json_response(
            "post",
            f"/experimental/textanalysis/projects/{project.name}/processes",
            json=request_json,
        )

        return response["payload"]

    @experimental_api
    def _get_process(
        self,
        document_collection: DocumentCollection,
        process_name: str,
    ) -> Process:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use DocumentCollection.get_process() instead.
        """
        project = document_collection.project

        response = self.__request_with_json_response(
            "get",
            f"/experimental/textanalysis/projects/{project.name}/"
            f"documentSources/{document_collection.name}/processes/{process_name}",
        )

        process_details = response["payload"]

        preceding_process_name = None
        if "precedingProcessName" in process_details:
            preceding_process_name = process_details["precedingProcessName"]

        return Process(
            project=project,
            name=process_details["processName"],
            pipeline_name=process_details["pipelineName"],
            document_source_name=process_details["documentSourceName"],
            preceding_process_name=preceding_process_name,
        )

    @experimental_api
    def _get_process_state(self, project: "Project", process: "Process") -> Process.ProcessState:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Process.get_process_state() instead.
        """
        response = self.__request_with_json_response(
            "get",
            f"/experimental/textanalysis/projects/{project.name}/"
            f"documentSources/{process.document_source_name}/processes/{process.name}",
        )
        process_details = response["payload"]

        if "processedDocuments" in process_details:
            # todo: delete this if condition when v6 is released
            return Process.ProcessState(
                process=process,
                state=process_details.get("state"),
                processed_documents=process_details.get("processedDocuments"),
            )
        else:
            return Process.ProcessState(
                process=process,
                state=process_details.get("state"),
                number_of_total_documents=process_details.get("numberOfTotalDocuments"),
                number_of_successful_documents=process_details.get("numberOfSuccessfulDocuments"),
                number_of_unsuccessful_documents=process_details.get(
                    "numberOfUnsuccessfulDocuments"
                ),
                error_messages=process_details.get("errorMessages"),
                preceding_process_name=process_details.get("precedingProcessName"),
            )

    @experimental_api
    def _delete_process(
        self, project_name: str, process_name: str, document_source_name: str
    ) -> None:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Process.delete() instead.
        """
        self.__request_with_json_response(
            "delete",
            f"/experimental/textanalysis/projects/{project_name}/"
            f"documentSources/{document_source_name}/processes/{process_name}",
        )
        return None

    @experimental_api
    def _reprocess(self, project_name: str, process_name: str, document_source_name: str) -> None:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use Process.rerun() instead.
        """
        self.__request_with_json_response(
            "post",
            f"/experimental/textanalysis/projects/{project_name}/"
            f"documentSources/{document_source_name}/processes/{process_name}/reprocess",
        )
        return None

    @experimental_api
    def _list_resources(self, project_name=None, pipeline_name=None) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use {client, project, pipeline}.list_resources() instead.
        """
        endpoint = self.__get_resources_endpoint(pipeline_name, project_name)
        return self.__request_with_json_response("get", endpoint)["payload"]

    @experimental_api
    def _delete_resources(self, project_name=None, pipeline_name=None) -> None:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use {client, project, pipeline}.delete_resources() instead.
        """
        endpoint = self.__get_resources_endpoint(pipeline_name, project_name)
        self.__request_with_json_response("delete", endpoint)

    @experimental_api
    def _upload_resources(self, zip_file: IO, project_name=None, pipeline_name=None) -> dict:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use {client, project, pipeline}.upload_resources() instead.
        """

        response = self.__request_with_json_response(
            "post",
            self.__get_resources_endpoint(project_name=project_name, pipeline_name=pipeline_name),
            files={"resourcesFile": ("zip_file.name", zip_file, "application/zip")},
        )

        return response["payload"]

    @experimental_api
    def _download_resources(
        self, target_zip_path: Union[Path, str], project_name=None, pipeline_name=None
    ) -> None:
        """
        HIGHLY EXPERIMENTAL API - may soon change or disappear.

        Use {client, project, pipeline}.download_resources() instead.
        """
        if isinstance(target_zip_path, str):
            target_zip_path = Path(target_zip_path)

        target_zip_path.parent.mkdir(parents=True, exist_ok=True)
        zip_file = open(target_zip_path, "wb")
        response = self.__request_with_bytes_response(
            "get",
            self.__get_resources_endpoint(project_name=project_name, pipeline_name=pipeline_name),
            headers={HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_ZIP},
        )
        zip_file.write(response)
        zip_file.close()

    @staticmethod
    def __handle_error(raw_response: requests.Response):
        """
        Reports as much information about an error as possible.

        The error information is potentially composed of two parts:
            First, there can be information in the status_code and reason of the raw_response for general HTTPErrors
            Second, the response might actually contain json with some information in the keys "message" or "errorMessages"
        """
        status_code = raw_response.status_code
        reason = raw_response.reason
        url = raw_response.url

        error_msg = ""
        if isinstance(reason, bytes):
            # We attempt to decode utf-8 first because some servers
            # choose to localize their reason strings. If the string
            # isn't utf-8, we fall back to iso-8859-1 for all other
            # encodings.
            try:
                reason = reason.decode("utf-8")
            except UnicodeDecodeError:
                reason = reason.decode("iso-8859-1")

        if 400 <= status_code < 500:
            error_msg = f"{status_code} Server Error: '{reason}' for url: '{url}'."

        elif 500 <= status_code < 600:
            error_msg = f"{status_code} Server Error: '{reason}' for url: '{url}'."

        try:
            response = raw_response.json()

            # Accessing an endpoint that is in the subdomain of the platform, but which does not exist,
            # returns a general servlet with a field "message"
            if "message" in response and response["message"] is not None:
                error_msg += f"\nPlatform error message is: '{response['message']}'"

            # Accessing an existing endpoint that has an error, returns its error in "errorMessages"
            if "errorMessages" in response and response["errorMessages"] is not None:
                error_msg += (
                    f"\nEndpoint error message is: '{', '.join(response['errorMessages'])}'"
                )
        except JSONDecodeError:
            pass

        raise RequestException(error_msg)

    @staticmethod
    def __process_name(process: Union[str, Process]):
        return process.name if isinstance(process, Process) else process

    @staticmethod
    def __pipeline_name(pipeline: Union[str, Pipeline]):
        return pipeline.name if isinstance(pipeline, Pipeline) else pipeline

    @staticmethod
    def __document_collection_name(document_collection: Union[str, DocumentCollection]):
        return (
            document_collection.name
            if isinstance(document_collection, DocumentCollection)
            else document_collection
        )

    @staticmethod
    def __get_resources_endpoint(pipeline_name, project_name):
        endpoint = "/experimental/textanalysis/"
        if project_name:
            endpoint += f"projects/{project_name}/"
            if pipeline_name:
                endpoint += f"pipelines/{pipeline_name}/"
        endpoint += "resources"
        return endpoint

    @staticmethod
    def _create_zip_io(source: Union[IO, Path, str], path_in_zip: Union[Path, str] = "") -> IO:

        if isinstance(source, (IO, BufferedReader)):
            return source

        if isinstance(source, str):
            source = Path(source)

        if not source.exists():
            raise Exception(f"{source} does not exist.")

        if zipfile.is_zipfile(source):
            if path_in_zip:
                raise Exception(
                    f"{source.name} is already a zip. Nesting the zip using path_in_zip is not supported."
                )
            return open(source, "rb")

        if isinstance(source, str):
            source = Path(source)
        if isinstance(path_in_zip, str):
            path_in_zip = Path(path_in_zip)

        zip_archive = BytesIO()
        with zipfile.ZipFile(zip_archive, "w", zipfile.ZIP_DEFLATED) as zip_file:
            if source.is_file():
                zip_file.write(filename=source, arcname=path_in_zip / source.name)

            elif source.is_dir():
                if not any(os.scandir(source)):
                    raise Exception(f"{source.name} is empty.")

                for dir_path, dir_names, file_names in os.walk(source):
                    for filename in file_names:
                        rel_path = Path(os.path.relpath(dir_path, source))
                        arcname = path_in_zip / rel_path / filename
                        filepath = Path(dir_path) / Path(filename)
                        zip_file.write(filename=filepath, arcname=arcname)

        zip_archive.seek(0)
        return zip_archive
