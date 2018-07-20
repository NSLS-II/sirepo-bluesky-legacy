import requests
import time

class SirepoBluesky(object):
    """
    Invoke a remote sirepo simulation with custom arguments.

    Parameters
    ----------
    server: str
        Sirepo server to call, ex. 'http://locahost:8000'

    Examples
    --------
    sim_id = '1tNWph0M'
    sb = SirepoBluesky('http://localhost:8000')
    data = sb.auth('srw', sim_id)
    # update the model values and choose the report
    data['models']['undulator']['verticalAmplitude'] = 0.95
    data['report'] = 'trajectoryReport'
    sb.run_simulation()
    f = sb.get_datafile()

    # assumes there is an aperture named A1 and a watchpoint named W1 in the beamline
    aperture = sb.find_element(data['models']['beamline'], 'title', 'A1')
    aperture['horizontalSize'] = 0.1
    aperture['verticalSize'] = 0.1
    watch = sb.find_element(data['models']['beamline'], 'title', 'W1')
    data['report'] = 'watchpointReport{}'.format(watch['id'])
    sb.run_simulation()
    f2 = sb.get_datafile()

    """
    def __init__(self, server):
        self.server = server

    def auth(self, sim_type, sim_id):
        """ Connect to the server and returns the data for the simulation identified by sim_id. """
        self.cookies = None
        res = self._post_json('bluesky-auth', {
            'simulationType': sim_type,
            'simulationId': sim_id,
        })
        assert 'state' in res and res['state'] == 'ok', 'bluesky_auth failed: {}'.format(res)
        self.sim_type = sim_type
        self.sim_id = sim_id
        self.res = res
        self.data = res['data']
        return self.data

    @staticmethod
    def find_element(elements, field, value):
        """ Helper method to lookup an element in an array by field value. """
        for e in elements:
            if e[field] == value:
                return e
        assert False, 'element not found, {}={}'.format(field, value)

    def get_datafile(self):
        """ Requests the raw datafile of simulation results from the server. Call auth() and run_simulation() before this. """
        assert hasattr(self, 'cookies'), 'call auth() before get_datafile()'
        url = 'download-data-file/{}/{}/{}/-1'.format(self.sim_type, self.sim_id, self.data['report'])
        response = requests.get('{}/{}'.format(self.server, url), cookies=self.cookies)
        self._assert_success(response, url)
        return response.content

    def run_simulation(self, max_status_calls=1000):
        """ Run the sirepo simulation and returns the formatted plot data.

        Parameters
        ----------
        max_status_calls: int, optional
            Maximum calls to check a running simulation's status. Roughly in seconds.
            Defaults is 1000.

        """
        assert hasattr(self, 'cookies'), 'call auth() before run_simulation()'
        assert 'report' in self.data, 'client needs to set data[\'report\']'
        self.data['simulationId'] = self.sim_id
        res = self._post_json('run-simulation', self.data)
        for _ in range(max_status_calls):
            state = res['state']
            if state == 'completed' or state == 'error':
                break
            time.sleep(res['nextRequestSeconds'])
            res = self._post_json('run-status', res['nextRequest'])
        assert state == 'completed', 'simulation failed to completed: {}'.format(state)
        return res

    @staticmethod
    def _assert_success(response, url):
        assert response.status_code == requests.codes.ok, '{} request failed, status: {}'.format(url, response.status_code)

    def _post_json(self, url, payload):
        response = requests.post('{}/{}'.format(self.server, url), json=payload, cookies=self.cookies)
        self._assert_success(response, url)
        if not self.cookies:
            self.cookies = response.cookies
        return response.json()
