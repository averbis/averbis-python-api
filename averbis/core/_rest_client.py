#
# Copyright (c) 2020 Averbis GmbH.
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
import importlib
import json
import logging
from concurrent.futures.thread import ThreadPoolExecutor
from io import BytesIO

from time import sleep, time
from typing import List, Union, IO, Iterable, Dict, TextIO, Iterator, Optional
from pathlib import Path
import requests

ENCODING_UTF_8 = "utf-8"

HEADER_ACCEPT = "Accept"
HEADER_CONTENT_TYPE = "Content-Type"

MEDIA_TYPE_ANY = "*/*"
MEDIA_TYPE_APPLICATION_XMI = "application/vnd.xmi+xml"
MEDIA_TYPE_APPLICATION_JSON = "application/json"
MEDIA_TYPE_APPLICATION_XML = "application/xml"
MEDIA_TYPE_TEXT_PLAIN_UTF8 = "text/plain; charset=utf-8"
MEDIA_TYPE_OCTET_STREAM = "application/octet-stream"

DOCUMENT_IMPORTER_CAS = "CAS Importer"
DOCUMENT_IMPORTER_SOLR = "Solr XML Importer"
DOCUMENT_IMPORTER_TEXT = "Text Importer"

TERMINOLOGY_IMPORTER_OBO = "OBO Importer"

TERMINOLOGY_EXPORTER_OBO_1_4 = "Obo 1.4 Exporter"
TERMINOLOGY_EXPORTER_SOLR_AUTO_SUGGEST_XML = "Solr Autosuggest XML Exporter"
TERMINOLOGY_EXPORTER_CONCEPT_DICTIONARY_XML = "Concept Dictionary XML Exporter"


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

    def delete(self) -> None:
        """
        Delete the pipeline from the server.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        self.project.client._delete_pipeline(self.project.name, self.name)

    def is_started(self) -> bool:
        """
        Checks if the pipeline has already started.

        :return: Whether the pipeline has started.
        """
        return self.get_info()["pipelineState"] == "STARTED"

    def analyse_text(self, source: Union[Path, IO, str], **kwargs) -> dict:
        """
        Analyze the given text or text file using the pipeline.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._analyse_text(self.project.name, self.name, source, **kwargs)

    def analyse_texts(
        self, sources: Iterable[Union[Path, IO, str]], parallelism: int = 0, **kwargs
    ) -> Iterator[Result]:
        """
        Analyze the given texts or files using the pipeline. If feasible, multiple documents are processed in parallel.

        :return: An iterator over the results produced by the pipeline.
        """
        pipeline_instances = self.get_configuration()["analysisEnginePoolSize"]
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
                return Result(data=self.analyse_text(source, **kwargs), source=source)
            except Exception as e:
                return Result(exception=e, source=source)

        with ThreadPoolExecutor(max_workers=parallel_request_count) as executor:
            return executor.map(run_analysis, sources)

    def analyse_html(self, source: Union[Path, IO, str], **kwargs) -> dict:
        """
        Analyze the given HTML string or HTML file using the pipeline.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        # noinspection PyProtectedMember
        return self.project.client._analyse_html(self.project.name, self.name, source, **kwargs)

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


class Project:
    def __init__(self, client: "Client", name: str):
        self.client = client
        self.name = name
        self.__cached_pipelines: dict = {}

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
        if name is not None:
            cfg = copy.deepcopy(configuration)
            cfg["name"] = name
        else:
            cfg = configuration

        self.client._create_pipeline(self.name, cfg)
        new_pipeline = Pipeline(self, cfg["name"])
        self.__cached_pipelines[cfg["name"]] = new_pipeline
        return new_pipeline

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
        return Terminology(self, response["payload"]["terminology_name"])

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


class Client:
    def __init__(
        self,
        url_or_id: str,
        api_token: str = None,
        verify_ssl: Union[str, bool] = None,
        settings: Union[str, Path, dict] = None,
    ):
        self.__logger = logging.getLogger(self.__class__.__module__ + "." + self.__class__.__name__)
        self._api_token = None
        self._verify_ssl = True

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

        if api_token:
            self._api_token = api_token

        if verify_ssl:
            self.verify_ssl = api_token

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

    def _load_settings(self, path: Union[str, Path] = None) -> dict:
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

    def ensure_available(self, timeout: int = 120) -> "Client":
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

        url = f"{self._url}/rest/{endpoint.lstrip('/')}"
        raw_response = requests.request(method, url, **kwargs)
        self.__logger.debug(
            "Response for %s %s: %s -- %s", method, url, raw_response, raw_response.content
        )
        return raw_response

    def __request(self, method: str, endpoint: str, **kwargs) -> dict:
        raw_response = self._run_request(method, endpoint, **kwargs)

        response = raw_response.json()
        self.__handle_error(response)
        return response

    def __request_with_bytes_response(self, method: str, endpoint: str, **kwargs) -> bytes:
        """
        A bytes response is used in the experimental API for encoding CAS objects.
        """
        raw_response = self._run_request(method, endpoint, **kwargs)

        is_actually_json_response = MEDIA_TYPE_APPLICATION_JSON in raw_response.headers.get(
            HEADER_CONTENT_TYPE, ""
        )
        if is_actually_json_response:
            raise TypeError(f"Expected the return content to be bytes, but got json.")

        raw_response.raise_for_status()
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
        response = self.__request(
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

        response = self.__request(
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

        response = self.__request(
            "put", f"/v1/users/{user}/apitoken", json={"password": password, "userSourceName": ""}
        )
        self._api_token = response["payload"]
        return self._api_token

    def invalidate_api_token(self, user: str, password: str) -> None:
        """
        Invalidates the API token for the given user. This method does not clear the API token from this client object.
        If the client is currently using the API token that is being cleared, subsequent operations will fail.
        """
        self.__request(
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
        response = self.__request(
            "post",
            f"/v1/users/{user}/apitoken/status",
            json={"password": password, "userSourceName": ""},
        )
        return response["payload"]

    def get_build_info(self) -> dict:
        """
        Obtains information about the version of the server instance.

        :return: The raw payload of the server response. Future versions of this library may return a better-suited
                 representation.
        """
        response = self.__request("get", f"/v1/buildInfo")
        return response["payload"]

    def create_project(self, name: str, description: str) -> Project:
        """
        Creates a new project.

        :return: The project.
        """
        response = self.__request(
            "post", f"/v1/projects", params={"name": name, "description": description}
        )
        return Project(self, response["payload"]["name"])

    def get_project(self, name: str) -> Project:
        """
        Access an existing project.

        :return: The project.
        """
        return Project(self, name)

    def list_projects(self) -> List[Project]:
        raise OperationNotSupported("Listing projects is not supported by the REST API yet")

    def _delete_project(self, name: str) -> None:
        """
        Use Project.delete() instead.
        """
        raise OperationNotSupported("Deleting projects is not supported by the REST API yet")

    def _list_terminologies(self, project: str) -> dict:
        """
        Use Project.list_terminologies() instead.
        """
        response = self.__request("get", f"/v1/terminology/projects/{project}/terminologies")
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
        response = self.__request(
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
        self.__request("delete", f"/v1/terminology/projects/{project}/terminologies/{terminology}")

    def _start_terminology_export(self, project: str, terminology: str, exporter: str) -> None:
        """
        Use Terminology.start_export() instead.
        """
        self.__request(
            "post",
            f"/v1/terminology/projects/{project}/terminologies/{terminology}/terminologyExports",
            params={"terminologyExporterName": exporter},
        )

    def _get_terminology_export_info(self, project: str, terminology: str) -> dict:
        """
        Use Terminology.get_export_status() instead.
        """
        response = self.__request(
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

        self.__request(
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
        response = self.__request(
            "get",
            f"/v1/terminology/projects/{project}/terminologies/{terminology}/terminologyImports",
            headers={HEADER_ACCEPT: MEDIA_TYPE_APPLICATION_JSON},
        )
        return response["payload"]

    def _create_pipeline(self, project: str, configuration: dict) -> Pipeline:
        response = self.__request(
            "post",
            f"/v1/textanalysis/projects/{project}/pipelines",
            json=configuration,
        )
        return response["payload"]

    def _delete_pipeline(self, project: str, pipeline: str) -> None:
        """
        Use Pipeline.delete() instead.
        """
        raise OperationNotSupported("Deleting pipelines is not supported by the REST API yet")

    def _start_pipeline(self, project: str, pipeline: str) -> dict:
        response = self.__request(
            "put", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/start"
        )
        return response["payload"]

    def _stop_pipeline(self, project: str, pipeline: str) -> dict:
        response = self.__request(
            "put", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/stop"
        )
        return response["payload"]

    def _get_pipeline_info(self, project: str, pipeline: str) -> dict:
        response = self.__request(
            "get", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}"
        )
        return response["payload"]

    def _get_pipeline_configuration(self, project: str, pipeline: str) -> dict:
        response = self.__request(
            "get", f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/configuration"
        )
        return response["payload"]

    def _set_pipeline_configuration(self, project: str, pipeline: str, configuration: dict) -> None:
        self.__request(
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
    ) -> dict:
        def get_media_type_for_format() -> str:
            if data_format == DOCUMENT_IMPORTER_TEXT:
                return MEDIA_TYPE_TEXT_PLAIN_UTF8
            else:
                return MEDIA_TYPE_OCTET_STREAM

        response = self.__request(
            "post",
            f"/v1/classification/projects/{project}/classificationSets/{classification_set}/classifyDocument",
            data=data,
            params={"type": data_format},
            headers={HEADER_CONTENT_TYPE: get_media_type_for_format()},
        )
        return response["payload"]

    def _analyse_text(
        self,
        project: str,
        pipeline: str,
        source: Union[Path, IO, str],
        annotation_types: str = None,
        language: str = "de",
    ) -> dict:
        if isinstance(source, Path):
            with source.open("r", encoding=ENCODING_UTF_8) as file:
                source = file.read()

        data: IO = BytesIO(source.encode(ENCODING_UTF_8)) if isinstance(source, str) else source

        response = self.__request(
            "post",
            f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/analyseText",
            data=data,
            params={"annotationTypes": annotation_types, "language": language},
            headers={HEADER_CONTENT_TYPE: MEDIA_TYPE_TEXT_PLAIN_UTF8},
        )
        return response["payload"]

    def _analyse_html(
        self,
        project: str,
        pipeline: str,
        source: Union[Path, IO, str],
        annotation_types: str = None,
        language: str = "de",
    ) -> dict:
        if isinstance(source, Path):
            with source.open("r", encoding=ENCODING_UTF_8) as file:
                source = file.read()

        data: IO = BytesIO(source.encode(ENCODING_UTF_8)) if isinstance(source, str) else source

        response = self.__request(
            "post",
            f"/v1/textanalysis/projects/{project}/pipelines/{pipeline}/analyseHtml",
            data=data,
            params={"annotationTypes": annotation_types, "language": language},
            headers={HEADER_CONTENT_TYPE: MEDIA_TYPE_TEXT_PLAIN_UTF8},
        )
        return response["payload"]

    def _select(self, project: str, q: str = None, **kwargs) -> dict:
        response = self.__request(
            "get",
            f"/v1/search/projects/{project}/select",
            params={"q": q, **kwargs},
            headers={HEADER_CONTENT_TYPE: MEDIA_TYPE_TEXT_PLAIN_UTF8},
        )
        return response["payload"]

    @staticmethod
    def __handle_error(response):
        if response["errorMessages"] is None or len(response["errorMessages"]) == 0:
            return

        raise Exception("Unable to perform request: " + ", ".join(response["errorMessages"]))
