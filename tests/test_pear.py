from averbis import Pear
from fixtures import *


@pytest.fixture()
def pear(client) -> Pear:
    project = client.get_project("LoadTesting")
    return Pear(project, "my_pear_component")


def test_get_parameter(pear, requests_mock):
    configuration = {
        'param0': 'value0',
        'param1': 'value1'
    }
    requests_mock.get(
        f"{API_EXPERIMENTAL}/textanalysis/projects/LoadTesting/pearComponents/{pear.identifier}",
        json={
            "payload": configuration,
            "errorMessages": [],
        }
    )
    actual_configuration = pear.get_default_configuration()
    assert configuration['param0'] == actual_configuration['param0']
    assert configuration['param1'] == actual_configuration['param1']
