import requests
import time
import random
import numconv
import hashlib
from pykern import pkcollections
import base64

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
    data, schema = sb.auth('srw', sim_id)
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
    def __init__(self, server, secret='bluesky'):
        self.server = server
        self.secret = secret

    def auth_hash(self, req, verify=False):
        _AUTH_HASH_SEPARATOR = ':'
        _AUTH_NONCE_CHARS = numconv.BASE62
        _AUTH_NONCE_UNIQUE_LEN = 32
        _AUTH_NONCE_SEPARATOR = '-'
        _AUTH_NONCE_REPLAY_SECS = 10

        now = int(time.time())
        if not 'authNonce' in req:
            if verify:
                raise ValueError('authNonce: missing field in request')
            r = random.SystemRandom()
            req['authNonce'] = str(now) + _AUTH_NONCE_SEPARATOR + ''.join(
                r.choice(_AUTH_NONCE_CHARS) for x in
                range(_AUTH_NONCE_UNIQUE_LEN)
            )
        h = hashlib.sha256()
        h.update(
            _AUTH_HASH_SEPARATOR.join([
                req['authNonce'],
                req['simulationType'],
                req['simulationId'],
                self.secret,
            ]).encode())
        res = 'v1:' + base64.urlsafe_b64encode(h.digest()).decode()
        if not verify:
            req['authHash'] = res
            return
        if res != req['authHash']:
            raise ValueError(
                '{}: hash mismatch expected={} nonce={}'.format(req['authHash'],
                res, req['authNonce']),

            )
        t = req['authNonce'].split(_AUTH_NONCE_SEPARATOR)[0]
        try:
            t = int(t)
        except ValueError as e:
            raise ValueError(
                '{}: auth_nonce prefix not an int: nonce={}'.format(t,
                req['authNonce']),
            )
        delta = now - t
        if abs(delta) > _AUTH_NONCE_REPLAY_SECS:
            raise ValueError(
                '{}: auth_nonce time outside replay window={} now={} nonce={}'.
                    format(t,_AUTH_NONCE_REPLAY_SECS, now, req['authNonce']),
            )

    def auth(self, sim_type, sim_id):
        """ Connect to the server and returns the data for the simulation identified by sim_id. """
        from pykern import pkconfig
        pkconfig.reset_state_for_testing({'SIREPO_BLUESKY_AUTH_SECRET' : 'secret'})


        req = dict(simulationType=sim_type, simulationId=sim_id)
        r = random.SystemRandom()
        req['authNonce'] = str(int(time.time())) + '-' + ''.join(r.choice
                                        (numconv.BASE62) for x in range(32))
        h = hashlib.sha256()
        h.update(':'.join([req['authNonce'], req['simulationType'],
                           req['simulationId'], self.secret]).encode())

        req['authHash'] = 'v1:' + base64.urlsafe_b64encode(h.digest()).decode()
        self.auth_hash(req, verify=True)

        self.cookies = None
        res = self._post_json('bluesky-auth', {
            'simulationType': sim_type,
            'simulationId': sim_id,
        })
        assert 'state' in res and res['state'] == 'ok', 'bluesky_auth failed: {}'.format(res)
        self.sim_type = sim_type
        self.sim_id = sim_id
        self.schema = res['schema']
        self.data = res['data']
        return self.data, self.schema

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
