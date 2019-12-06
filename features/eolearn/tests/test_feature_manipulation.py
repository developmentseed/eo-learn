"""
Credits:
Copyright (c) 2017-2019 Matej Aleksandrov, Matej Batič, Andrej Burja, Eva Erzin (Sinergise)
Copyright (c) 2017-2019 Grega Milčinski, Matic Lubej, Devis Peresutti, Jernej Puc, Tomislav Slijepčević (Sinergise)
Copyright (c) 2017-2019 Blaž Sovdat, Nejc Vesel, Jovan Višnjić, Anže Zupanc, Lojze Žust (Sinergise)

This source code is licensed under the MIT license found in the LICENSE
file in the root directory of this source tree.
"""

import unittest
import datetime

from eolearn.features import FilterTimeSeries, ValueFilloutTask
from eolearn.core import EOPatch, FeatureType

import numpy as np


class TestFeatureManipulation(unittest.TestCase):

    def test_content_after_timefilter(self):
        timestamps = [datetime.datetime(2017, 1, 1, 10, 4, 7),
                      datetime.datetime(2017, 1, 4, 10, 14, 5),
                      datetime.datetime(2017, 1, 11, 10, 3, 51),
                      datetime.datetime(2017, 1, 14, 10, 13, 46),
                      datetime.datetime(2017, 1, 24, 10, 14, 7),
                      datetime.datetime(2017, 2, 10, 10, 1, 32),
                      datetime.datetime(2017, 2, 20, 10, 6, 35),
                      datetime.datetime(2017, 3, 2, 10, 0, 20),
                      datetime.datetime(2017, 3, 12, 10, 7, 6),
                      datetime.datetime(2017, 3, 15, 10, 12, 14)]
        data = np.random.rand(10, 100, 100, 3)

        new_start = 4
        new_end = -3

        old_interval = (timestamps[0], timestamps[-1])
        new_interval = (timestamps[new_start], timestamps[new_end])

        new_timestamps = [ts for ts in timestamps[new_start:new_end+1]]

        eop = EOPatch(timestamp=timestamps,
                      data={'data': data},
                      meta_info={'time_interval': old_interval})

        filter_task = FilterTimeSeries(start_date=new_interval[0], end_date=new_interval[1])
        filter_task.execute(eop)

        updated_interval = eop.meta_info['time_interval']
        updated_timestamps = eop.timestamp

        self.assertEqual(new_interval, updated_interval)
        self.assertEqual(new_timestamps, updated_timestamps)

    def test_value_fillout(self):
        feature = (FeatureType.DATA, 'TEST')
        shape = (8, 10, 10, 5)
        data = np.random.randint(0, 100, size=shape).astype(np.float)
        eopatch = EOPatch(data={'TEST': data})

        self.assertRaises(ValueError, ValueFilloutTask, feature, operations='x')
        self.assertRaises(ValueError, ValueFilloutTask, feature, operations=4)

        self.assertRaises(ValueError, ValueFilloutTask.fill, None, operation='f')
        self.assertRaises(ValueError, ValueFilloutTask.fill, np.zeros((4, 5)), operation='x')

        # nothing to be filled, return the same eopatch object immediately
        eopatch_new = ValueFilloutTask(feature, operations='fb', axis=0)(eopatch)
        self.assertEqual(eopatch, eopatch_new)

        eopatch[feature][0, 0, 0, :] = np.nan

        def execute_fillout(eopatch, feature, **kwargs):
            input_array = eopatch[feature]
            eopatch = ValueFilloutTask(feature, **kwargs)(eopatch)
            output_array = eopatch[feature]
            return eopatch, input_array, output_array

        # filling forward temporally should not fill nans
        eopatch, input_array, output_array = execute_fillout(eopatch, feature, operations='f', axis=0)
        compare_mask = ~np.isnan(input_array)
        self.assertTrue(np.isnan(output_array[0, 0, 0, :]).all())
        self.assertTrue(np.array_equal(input_array[compare_mask], output_array[compare_mask]))
        self.assertNotEqual(id(input_array), id(output_array))

        # filling in any direction along axis=-1 should also not fill nans since all neighbors are nans
        eopatch, input_array, output_array = execute_fillout(eopatch, feature, operations='fb', axis=-1)
        self.assertTrue(np.isnan(output_array[0, 0, 0, :]).all())
        self.assertNotEqual(id(input_array), id(output_array))

        # filling nans backwards temporally should fill nans
        eopatch, input_array, output_array = execute_fillout(eopatch, feature, operations='b', axis=0)
        self.assertFalse(np.isnan(output_array).any())
        self.assertNotEqual(id(input_array), id(output_array))

        # try filling something else than nan (e.g.: -1)
        eopatch[feature][0, :, 0, 0] = -1
        eopatch, input_array, output_array = execute_fillout(eopatch, feature, operations='b', value=-1, axis=-1)
        self.assertFalse((output_array == -1).any())
        self.assertNotEqual(id(input_array), id(output_array))

        # [nan, 1, nan, 2, ... ]  ---('fb')---> [1, 1, 1, 2, ... ]
        eopatch[feature][0, 0, 0, 0:4] = [np.nan, 1, np.nan, 2]
        eopatch, input_array, output_array = execute_fillout(eopatch, feature, operations='fb', axis=-1)
        self.assertTrue(np.array_equal(output_array[0, 0, 0, 0:4], [1, 1, 1, 2]))
        self.assertNotEqual(id(input_array), id(output_array))

        # [nan, 1, nan, 2, ... ]  ---('bf')---> [1, 1, 2, 2, ... ]
        eopatch[feature][0, 0, 0, 0:4] = [np.nan, 1, np.nan, 2]
        eopatch, input_array, output_array = execute_fillout(eopatch, feature, operations='bf', axis=-1)
        self.assertTrue(np.array_equal(output_array[0, 0, 0, 0:4], [1, 1, 2, 2]))
        self.assertNotEqual(id(input_array), id(output_array))


if __name__ == '__main__':
    unittest.main()
