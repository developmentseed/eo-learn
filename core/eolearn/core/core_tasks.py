"""
A collection of most basic EOTasks
"""

import os
import numpy as np
from copy import deepcopy

from .eodata import EOPatch
from .eotask import EOTask


class CopyTask(EOTask):
    """Makes a shallow copy of the given EOPatch.

    It copies feature type dictionaries but not the data itself.

    """
    def __init__(self, features=...):
        """
        :param features: A collection of features or feature types that will be copied into new EOPatch.
        :type features: object supported by eolearn.core.utilities.FeatureParser class
        """
        self.features = features

    def execute(self, eopatch):
        return eopatch.__copy__(features=self.features)


class DeepCopyTask(CopyTask):
    """ Makes a deep copy of the given EOPatch.
    """
    def execute(self, eopatch):
        return eopatch.__deepcopy__(features=self.features)


class SaveToDisk(EOTask):
    """Saves the given EOPatch to disk.
    """
    def __init__(self, folder, *args, **kwargs):
        """
        :param folder: root directory where all EOPatches are saved
        :type folder: str
        :param features: A collection of features types specifying features of which type will be saved. By default
            all features will be saved.
        :type features: object supported by eolearn.core.utilities.FeatureParser class
        :param file_format: File format
        :type file_format: FileFormat or str
        :param overwrite_permission: A level of permission for overwriting an existing EOPatch
        :type overwrite_permission: OverwritePermission or int
        :param compress_level: A level of data compression and can be specified with an integer from 0 (no compression)
            to 9 (highest compression).
        :type compress_level: int
        """
        self.folder = folder
        self.args = args
        self.kwargs = kwargs

    def execute(self, eopatch, *, eopatch_folder):
        """Saves the EOPatch to disk: `folder/eopatch_folder`.

        :param eopatch: EOPatch which will be saved
        :type eopatch: EOPatch
        :param eopatch_folder: name of EOPatch folder containing data
        :type eopatch_folder: str
        :return: The same EOPatch
        :rtype: EOPatch
        """
        eopatch.save(os.path.join(self.folder, eopatch_folder), *self.args, **self.kwargs)
        return eopatch


class LoadFromDisk(EOTask):
    """Loads the given EOPatch from disk.
    """
    def __init__(self, folder, *args, **kwargs):
        """
        :param folder: root directory where all EOPatches are saved
        :type folder: str
        :param features: A collection of features to be loaded. By default all features will be loaded.
        :type features: object supported by eolearn.core.utilities.FeatureParser class
        :param lazy_loading: If `True` features will be lazy loaded. Default is `False`
        :type lazy_loading: bool
        :param mmap: If `True`, then memory-map the file. Works only on uncompressed npy files
        :type mmap: bool
        """
        self.folder = folder
        self.args = args
        self.kwargs = kwargs

    def execute(self, *, eopatch_folder):
        """Loads the EOPatch from disk: `folder/eopatch_folder`.

        :param eopatch_folder: name of EOPatch folder containing data
        :type eopatch_folder: str
        :return: EOPatch loaded from disk
        :rtype: EOPatch
        """
        eopatch = EOPatch.load(os.path.join(self.folder, eopatch_folder), *self.args, **self.kwargs)
        return eopatch


class AddFeature(EOTask):
    """Adds a feature to the given EOPatch.
    """
    def __init__(self, feature):
        """
        :param feature: Feature to be added
        :type feature: (FeatureType, feature_name) or FeatureType
        """
        self.feature_type, self.feature_name = next(self._parse_features(feature)())

    def execute(self, eopatch, data):
        """Returns the EOPatch with added features.

        :param eopatch: input EOPatch
        :type eopatch: EOPatch
        :param data: data to be added to the feature
        :type data: object
        :return: input EOPatch with the specified feature
        :rtype: EOPatch
        """
        if self.feature_name is None:
            eopatch[self.feature_type] = data
        else:
            eopatch[self.feature_type][self.feature_name] = data

        return eopatch


class RemoveFeature(EOTask):
    """Removes one or multiple features from the given EOPatch.
    """
    def __init__(self, features):
        """
        :param features: A collection of features to be removed.
        :type features: object supported by eolearn.core.utilities.FeatureParser class
        """
        self.feature_gen = self._parse_features(features)

    def execute(self, eopatch):
        """Returns the EOPatch with removed features.

        :param eopatch: input EOPatch
        :type eopatch: EOPatch
        :return: input EOPatch without the specified feature
        :rtype: EOPatch
        """
        for feature_type, feature_name in self.feature_gen(eopatch):
            if feature_name is ...:
                eopatch.reset_feature_type(feature_type)
            else:
                del eopatch[feature_type][feature_name]

        return eopatch


class RenameFeature(EOTask):
    """Renames one or multiple features from the given EOPatch.
    """
    def __init__(self, features):
        """
        :param features: A collection of features to be renamed.
        :type features: object supported by eolearn.core.utilities.FeatureParser class
        """
        self.feature_gen = self._parse_features(features, new_names=True)

    def execute(self, eopatch):
        """Returns the EOPatch with renamed features.

        :param eopatch: input EOPatch
        :type eopatch: EOPatch
        :return: input EOPatch with the renamed features
        :rtype: EOPatch
        """
        for feature_type, feature_name, new_feature_name in self.feature_gen(eopatch):
            eopatch[feature_type][new_feature_name] = eopatch[feature_type][feature_name]
            del eopatch[feature_type][feature_name]

        return eopatch

class DuplicateFeature(EOTask):
    """Duplicates one or multiple features in an EOPatch.
    """

    def __init__(self, features, deep_copy_data=False):
        """
        :param features: A collection of features to be copied.
        :type features: object supported by eolearn.core.utilities.FeatureParser class
        """
        self.feature_gen = self._parse_features(features, new_names=True)
        self.deep = deep_copy_data

    def execute(self, eopatch):
        """Returns the EOPatch with copied features.

        :param eopatch: Input EOPatch
        :type eopatch: EOPatch
        :return: Input EOPatch with the duplicated features.
        :rtype: EOPatch
        :raises ValueError: Raises an exception when trying to duplicate a feature with an
            already existing feature name.
        """

        for feature_type, feature_name, new_feature_name in self.feature_gen(eopatch):
            if new_feature_name in eopatch[feature_type]:
                raise ValueError("A feature named '{}' already exists.".format(new_feature_name))

            if self.deep:
                eopatch[feature_type][new_feature_name] = deepcopy(eopatch[feature_type][feature_name])
            else:
                eopatch[feature_type][new_feature_name] = eopatch[feature_type][feature_name]

        return eopatch


class InitializeFeature(EOTask):
    """ Initalizes the values of a feature.

    Example:

    .. code-block:: python

        InitializeFeature((FeatureType.DATA, 'data1'), shape=(5, 10, 10, 3), init_value=3)

        # Initialize data of the same shape as (FeatureType.DATA, 'data1')
        InitializeFeature((FeatureType.MASK, 'mask1'), shape=(FeatureType.DATA, 'data1'), init_value=1)

    """
    def __init__(self, feature, shape, init_value=0, dtype=np.uint8):
        """
        :param feature: A collection of features to initialize.
        :type feature: An object supported by eolearn.core.utilities.FeatureParser class.
        :param shape: A shape object (t, n, m, d) or a feature from which to read the shape.
        :type feature: A tuple or an object supported by eolearn.core.utilities.FeatureParser class.
        :param init_value: A value with which to initialize the array of the new feature.
        :type init_value: int
        :param dtype: Type of array values.
        :type dtype: NumPy dtype
        :raises ValueError: Raises an exeption when passing the wrong shape argument.
        """

        self.new_features = self._parse_features(feature)

        try:
            self.shape_feature = next(self._parse_features(shape)())
        except ValueError:
            self.shape_feature = None

        if self.shape_feature:
            self.shape = None
        elif isinstance(shape, tuple) and len(shape) in (3, 4) and all(isinstance(x, int) for x in shape):
            self.shape = shape
        else:
            raise ValueError("shape argument is not a shape tuple or a feature containing one.")

        self.init_value = init_value
        self.dtype = dtype

    def execute(self, eopatch):
        """
        :param eopatch: Input EOPatch.
        :type eopatch: EOPatch
        :return: Input EOPatch with the initialized aditional features.
        :rtype: EOPatch
        """
        shape = eopatch[self.shape_feature].shape if self.shape_feature else self.shape

        add_features = set(self.new_features) - set(eopatch.get_feature_list())

        for feature in add_features:
            eopatch[feature] = np.ones(shape, dtype=self.dtype) * self.init_value

        return eopatch
