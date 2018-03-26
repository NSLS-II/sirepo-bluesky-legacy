import datetime
from pathlib import Path

from bluesky.tests.utils import _print_redirect

from ophyd import Device, Signal, Component as Cpt
from ophyd.sim import SynAxis, NullStatus, new_uid

from srw_run import srw_run
from srw_handler import read_srw_file


class SRWDetector(Device):
    """
    Use SRW code based on the value of the motor.

    Parameters
    ----------
    name : str
        The name of the detector

    TODO: complete doc-string.
    """
    image = Cpt(Signal)
    shape = Cpt(Signal)
    mean = Cpt(Signal)
    photon_energy = Cpt(Signal)
    horizontal_extent = Cpt(Signal)
    vertical_extent = Cpt(Signal)

    def __init__(self, name, motor0, field0, motor1, field1, reg=None,
                 **kwargs):
        super().__init__(name=name, **kwargs)
        self.reg = reg
        self._motor0 = motor0
        self._motor1 = motor1
        self._field0 = field0
        self._field1 = field1
        self._resource_id = None
        self._result = {}
        self._hints = None

    @property
    def hints(self):
        if self._hints is None:
            return {'fields': [self.mean.name]}
        return self._hints

    @hints.setter
    def hints(self, val):
        self._hints = dict(val)

    def trigger(self):
        super().trigger()
        x = self._motor0.read()[self._field0]['value']
        y = self._motor1.read()[self._field1]['value']
        datum_id = new_uid()
        date = datetime.datetime.now()
        srw_file = Path('/tmp/data') / Path(date.strftime('%Y/%m/%d')) / \
            Path('{}.dat'.format(datum_id))
        with _print_redirect():
            srw_run(str(srw_file), slit_x_width=x, slit_y_width=y)
            ret = read_srw_file(srw_file)
        self.image.put(datum_id)
        self.shape.put(ret['shape'])
        self.mean.put(ret['mean'])
        self.photon_energy.put(ret['photon_energy'])
        self.horizontal_extent.put(ret['horizontal_extent'])
        self.vertical_extent.put(ret['vertical_extent'])

        self._resource_id = self.reg.insert_resource('srw', srw_file, {})
        self.reg.insert_datum(self._resource_id, datum_id, {})

        return NullStatus()

    def describe(self):
        res = super().describe()
        res[self.image.name].update(dict(external="FILESTORE"))
        return res

    def unstage(self):
        self._resource_id = None
        self._result.clear()


class FakeSlits(Device):
    xwidth = Cpt(SynAxis, delay=0.01)
    ywidth = Cpt(SynAxis, delay=0.02)


fs = FakeSlits(name='fs')
srw_det = SRWDetector('srw_det', fs.xwidth, 'fs_xwidth',
                      fs.ywidth, 'fs_ywidth', reg=db.reg)
srw_det.read_attrs = ['image', 'mean', 'photon_energy']
srw_det.configuration_attrs = ['horizontal_extent', 'vertical_extent', 'shape']
