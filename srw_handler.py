import numpy as np
import uti_plot_com as srw_io


def read_srw_file(filename):
    data, mode, ranges, labels, units = srw_io.file_load(filename)
    data = np.array(data).reshape((ranges[8], ranges[5]), order='C')
    return {'data': data,
            'shape': data.shape,
            'mean': np.mean(data),
            'photon_energy': ranges[0],
            'horizontal_extent': ranges[3:5],
            'vertical_extent': ranges[6:8],
            # 'mode': mode,
            'labels': labels,
            'units': units}


class SRWFileHandler:
    specs = {'srw'}

    def __init__(self, filename):
        self._name = filename

    def __call__(self):
        d = read_srw_file(self._name)
        return d['data']
