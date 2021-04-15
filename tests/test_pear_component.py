from averbis import PearComponent
from fixtures import *


@pytest.fixture()
def pear_component(client) -> PearComponent:
    project = client.get_project("LoadTesting")
    return PearComponent(project, "my_pear_component")


def test_get_parameter(pear_component, requests_mock):
    configuration = {
        'param0': 'value0',
        'param1': 'value1'
    }
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents/{pear_component.identifier}",
        json={
            "payload": configuration,
            "errorMessages": [],
        }
    )
    actual_configuration = pear_component.get_default_configuration()
    assert configuration['param0'] == actual_configuration['param0']
    assert configuration['param1'] == actual_configuration['param1']
