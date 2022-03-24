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
import click as click
from cassis import load_typesystem, load_cas_from_xmi

from averbis import Client

DEFAULT_TYPE_SYSTEM_FILE = 'typesystem.xml'

@click.group(help="CLI tool for Averbis")
def cli():
    pass


@click.group(name="project", help="Commands related to projects")
def project_group():
    pass


@click.command(name="list", help="Show list of projects")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
def list_projects(server: str):
    client = Client(server)
    for project in client.list_projects():
        click.echo(project)


@click.command(name="create", help="Create a project")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
def create_project(server: str, project_name: str):
    client = Client(server)
    result = client.create_project(project_name)
    click.echo(f'CREATED: {result}')


@click.command(name="delete", help="Delete a project")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
def delete_project(server: str, project_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    project.delete()
    click.echo(f'DELETED: {project}')


@click.group(name="collection", help="Commands related to collections")
def collection_group():
    pass


@click.command(name="list", help="Show list of document collections")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
def list_collections(server: str, project_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    for collection in project.list_document_collections():
        click.echo(collection)


@click.command(name="create", help="Create a document collections")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
@click.argument("collection_name")
def create_collection(server: str, project_name: str, collection_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.create_document_collection(collection_name)
    click.echo(f'CREATED: {collection}')


@click.command(name="delete", help="Delete a document collections")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
@click.argument("collection_name")
def delete_collection(server: str, project_name: str, collection_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.get_document_collection(collection_name)
    collection.delete()
    click.echo(f'DELETED: {collection}')


@click.group(name="document", help="Commands related to documents")
def document_group():
    pass


@click.command(name="list", help="Show list of documents")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
@click.argument("collection_name")
def list_documents(server: str, project_name: str, collection_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.get_document_collection(collection_name)
    for document in collection.list_documents():
        click.echo(document)


@click.group(name="process", help="Commands related to processes")
def process_group():
    pass


@click.command(name="list", help="Show list of processes")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
@click.argument("collection_name")
def list_processes(server: str, project_name: str, collection_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.get_document_collection(collection_name)
    for process in collection.list_processes():
        click.echo(process)


@click.command(name="create", help="Create a process")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
@click.argument("collection_name")
@click.argument("process_name")
def create_process(server: str, project_name: str, collection_name: str, process_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.get_document_collection(collection_name)
    process = collection.create_process(process_name)
    click.echo(f'CREATED: {process}')


@click.command(name="delete", help="Delete a process")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.argument("project_name")
@click.argument("collection_name")
@click.argument("process_name")
def delete_process(server: str, project_name: str, collection_name: str, process_name: str):
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.get_document_collection(collection_name)
    process = collection.get_process(process_name)
    process.delete()
    click.echo(f'DELETED: {process}')


@click.group(name="annotation", help="Commands related to text analysis result")
def annotation_group():
    pass


@click.command(name="export", help="Export a text analysis result")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.option('-t', '--type-system', type=str, help='Type system file', default=DEFAULT_TYPE_SYSTEM_FILE)
@click.argument("project_name")
@click.argument("collection_name")
@click.argument("process_name")
@click.argument("document_name")
def export_annotation(server: str, project_name: str, collection_name: str, process_name: str, document_name: str, type_system_file: str):
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.get_document_collection(collection_name)
    process = collection.get_process(process_name)
    cas = process.export_text_analysis_to_cas(document_name)
    xmi_file_name = document_name + ".xmi" if not document_name.endswith(".xmi") else document_name
    cas.to_xmi(xmi_file_name, pretty_print=True)
    cas.typesystem.to_xml(type_system_file)
    click.echo(f'EXPORTED: {xmi_file_name}, {type_system_file}')


@click.command(name="import", help="Import a text analysis result")
@click.option('-S', '--server', type=str, help='Server to connect to (url or profile name)', default='default')
@click.option('-t', '--type-system', type=click.File('rb'), help='Type system file', default=DEFAULT_TYPE_SYSTEM_FILE)
@click.argument("project_name")
@click.argument("collection_name")
@click.argument("process_name")
@click.argument("file", type=click.File('rb'))
def import_annotation(server: str, project_name: str, collection_name: str, process_name: str, file, type_system_file):
    typesystem = load_typesystem(type_system_file)
    cas = load_cas_from_xmi(file, typesystem=typesystem)
    client = Client(server)
    project = client.get_project(project_name)
    collection = project.get_document_collection(collection_name)
    process = collection.get_process(process_name)
    process.import_text_analysis_result(cas, document_name=file.name)
    click.echo(f'IMPORTED: {file.name}')


cli.add_command(project_group)
project_group.add_command(list_projects)
project_group.add_command(create_project)
project_group.add_command(delete_project)

cli.add_command(collection_group)
collection_group.add_command(list_collections)
collection_group.add_command(create_collection)
collection_group.add_command(delete_collection)

cli.add_command(document_group)
document_group.add_command(list_documents)

cli.add_command(process_group)
process_group.add_command(list_processes)
process_group.add_command(create_process)
process_group.add_command(delete_process)

cli.add_command(annotation_group)
annotation_group.add_command(export_annotation)
