import unittest
import logging
import datetime
import numpy as np

from eolearn.core import EOPatch, FeatureType, CopyTask, DeepCopyTask, AddFeature, RemoveFeature, RenameFeature,\
    DuplicateFeature, InitializeFeature


logging.basicConfig(level=logging.DEBUG)


class TestCoreTasks(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.patch = EOPatch()

        cls.patch.data['bands'] = np.arange(2*3*3*2).reshape(2, 3, 3, 2)
        cls.patch.mask_timeless['mask'] = np.arange(3*3*2).reshape(3, 3, 2)
        cls.patch.scalar['values'] = np.arange(10*5).reshape(10, 5)
        cls.patch.timestamp = [datetime.datetime(2017, 1, 1, 10, 4, 7),
                               datetime.datetime(2017, 1, 4, 10, 14, 5),
                               datetime.datetime(2017, 1, 11, 10, 3, 51),
                               datetime.datetime(2017, 1, 14, 10, 13, 46),
                               datetime.datetime(2017, 1, 24, 10, 14, 7),
                               datetime.datetime(2017, 2, 10, 10, 1, 32),
                               datetime.datetime(2017, 2, 20, 10, 6, 35),
                               datetime.datetime(2017, 3, 2, 10, 0, 20),
                               datetime.datetime(2017, 3, 12, 10, 7, 6),
                               datetime.datetime(2017, 3, 15, 10, 12, 14)]
        cls.patch.bbox = (324.54, 546.45, 955.4, 63.43, 3857)
        cls.patch.meta_info['something'] = np.random.rand(10, 1)

    def test_copy(self):
        patch_copy = CopyTask().execute(self.patch)

        self.assertEqual(self.patch, patch_copy, 'Copied patch is different')

        patch_copy.data['new'] = np.arange(1).reshape(1, 1, 1, 1)
        self.assertFalse('new' in self.patch.data, 'Dictionary of features was not copied')

        patch_copy.data['bands'][0, 0, 0, 0] += 1
        self.assertTrue(np.array_equal(self.patch.data['bands'], patch_copy.data['bands']),
                        'Data should not be copied')

    def test_deepcopy(self):
        patch_deepcopy = DeepCopyTask().execute(self.patch)

        self.assertEqual(self.patch, patch_deepcopy, 'Deep copied patch is different')

        patch_deepcopy.data['new'] = np.arange(1).reshape(1, 1, 1, 1)
        self.assertFalse('new' in self.patch.data, 'Dictionary of features was not copied')

        patch_deepcopy.data['bands'][0, 0, 0, 0] += 1
        self.assertFalse(np.array_equal(self.patch.data['bands'], patch_deepcopy.data['bands']),
                         'Data should be copied')

    def test_partial_copy(self):
        partial_copy = DeepCopyTask(features=[(FeatureType.MASK_TIMELESS, 'mask'),
                                              FeatureType.BBOX]).execute(self.patch)
        expected_patch = EOPatch(mask_timeless=self.patch.mask_timeless, bbox=self.patch.bbox)
        self.assertEqual(partial_copy, expected_patch, 'Partial copying was not successful')

        partial_deepcopy = DeepCopyTask(features=[FeatureType.TIMESTAMP,
                                                  (FeatureType.SCALAR, 'values')]).execute(self.patch)
        expected_patch = EOPatch(scalar=self.patch.scalar, timestamp=self.patch.timestamp)
        self.assertEqual(partial_deepcopy, expected_patch, 'Partial deep copying was not successful')

    def test_add_rename_remove_feature(self):
        cloud_mask = np.arange(10).reshape(5, 2, 1, 1)
        feature_name = 'CLOUD MASK'
        new_feature_name = 'CLM'

        patch = AddFeature((FeatureType.MASK, feature_name))(self.patch, cloud_mask)
        self.assertTrue(np.array_equal(patch.mask[feature_name], cloud_mask), 'Feature was not added')

        patch = RenameFeature((FeatureType.MASK, feature_name, new_feature_name))(self.patch)
        self.assertTrue(np.array_equal(patch.mask[new_feature_name], cloud_mask), 'Feature was not renamed')
        self.assertFalse(feature_name in patch[FeatureType.MASK], 'Old feature still exists')

        patch = RemoveFeature((FeatureType.MASK, new_feature_name))(patch)
        self.assertFalse(feature_name in patch.mask, 'Feature was not removed')

    def test_duplicate_feature(self):
        mask_data = np.arange(10).reshape(5, 2, 1, 1)
        feature_name = 'MASK1'
        duplicate_name = 'MASK2'

        patch = AddFeature((FeatureType.MASK, feature_name))(self.patch, mask_data)

        duplicate_task = DuplicateFeature((FeatureType.MASK, feature_name, duplicate_name))
        patch = duplicate_task(patch)

        self.assertTrue(duplicate_name in patch.mask, 'Feature was not duplicated. Name not found.')
        self.assertEqual(id(patch.mask['MASK1']), id(patch.mask['MASK2']))
        self.assertTrue(np.array_equal(patch.mask[duplicate_name], mask_data),
                        'Feature was not duplicated correctly. Data does not match.')

        with self.assertRaises(ValueError, msg='Expected a ValueError when creating an already exising feature.'):
            patch = duplicate_task(patch)

        duplicate_names = {'D1', 'D2'}
        feature_list = [(FeatureType.MASK, 'MASK1', 'D1'), (FeatureType.MASK, 'MASK2', 'D2')]
        patch = DuplicateFeature(feature_list).execute(patch)

        self.assertTrue(duplicate_names.issubset(patch.mask.keys()), 'Duplicating multiple features failed.')

        patch = DuplicateFeature((FeatureType.MASK, 'MASK1', 'DEEP'), deep_copy_data=True)(patch)
        self.assertNotEqual(id(patch.mask['MASK1']), id(patch.mask['DEEP']))
        self.assertTrue(np.array_equal(patch.mask['MASK1'], patch.mask['DEEP']),
                        'Feature was not duplicated correctly. Data does not match.')

        # Duplicating MASK1 three times into D3, D4, D5 doesn't work, because EOTask.feature_gen
        # returns a dict containing only ('MASK1', 'D5') duplication

        # duplicate_names = {'D3', 'D4', 'D5'}
        # feature_list = [(FeatureType.MASK, 'MASK1', new) for new in duplicate_names]
        # patch = DuplicateFeature(feature_list).execute(patch)

        # self.assertTrue(duplicate_names.issubset(patch.mask.keys()),
        #                 'Duplicating single feature multiple times failed.')

    def test_initialize_feature(self):
        patch = DeepCopyTask()(self.patch)

        init_val = 123
        shape = (5, 10, 10, 3)
        compare_data = np.ones(shape) * init_val

        patch = InitializeFeature((FeatureType.MASK, 'test'), shape=shape, init_value=init_val)(patch)
        self.assertEqual(patch.mask['test'].shape, shape)
        self.assertTrue(np.array_equal(patch.mask['test'], compare_data))

        failmsg = 'Expected a ValueError when trying to initialize a feature with a wrong shape dmensions.'
        with self.assertRaises(ValueError, msg=failmsg):
            patch = InitializeFeature((FeatureType.MASK_TIMELESS, 'wrong'), shape=shape, init_value=init_val)(patch)

        init_val = 123
        shape = (10, 10, 3)
        compare_data = np.ones(shape) * init_val

        patch = InitializeFeature((FeatureType.MASK_TIMELESS, 'test'), shape=shape, init_value=init_val)(patch)
        self.assertEqual(patch.mask_timeless['test'].shape, shape)
        self.assertTrue(np.array_equal(patch.mask_timeless['test'], compare_data))

        fail_msg = 'Expected a ValueError when trying to initialize a feature with a wrong shape dmensions.'
        with self.assertRaises(ValueError, msg=fail_msg):
            patch = InitializeFeature((FeatureType.MASK, 'wrong'), shape=shape, init_value=init_val)(patch)

        init_val = 123
        shape = (5, 10, 10, 3)
        compare_data = np.ones(shape) * init_val
        new_names = {'F1', 'F2', 'F3'}

        patch = InitializeFeature({FeatureType.MASK: new_names}, shape=shape, init_value=init_val)(patch)
        fail_msg = "Failed to initialize new features from a shape tuple."
        self.assertTrue(new_names < set(patch.mask.keys()), msg=fail_msg)
        self.assertTrue(all(patch.mask[key].shape == shape for key in new_names))
        self.assertTrue(all(np.array_equal(patch.mask[key], compare_data) for key in new_names))

        patch = InitializeFeature({FeatureType.DATA: new_names}, shape=(FeatureType.DATA, 'bands'))(patch)
        fail_msg = "Failed to initialize new features from an existing feature."
        self.assertTrue(new_names < set(patch.data), msg=fail_msg)
        self.assertTrue(all(patch.data[key].shape == patch.data['bands'].shape for key in new_names))


if __name__ == '__main__':
    unittest.main()
