from averbis import PearComponent
from fixtures import *


@pytest.fixture()
def pear_component(client) -> PearComponent:
    project = client.get_project("LoadTesting")
    return PearComponent(project, "my_pear_component")


def test_get_parameter(pear_component, requests_mock):
    parameters = {
        'param0': 'value0',
        'param1': 'value1'
    }
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents/{pear_component.identifier}",
        json={
            "payload": parameters,
            "errorMessages": [],
        },
    )
    actual_parameters = pear_component.get_parameters()
    assert parameters['param0'] == actual_parameters['param0']
    assert parameters['param1'] == actual_parameters['param1']
