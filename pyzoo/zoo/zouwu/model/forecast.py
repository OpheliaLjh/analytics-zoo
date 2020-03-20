#
# Copyright 2018 Analytics Zoo Authors.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from abc import ABCMeta, abstractmethod

from zoo.automl.model.MTNet_keras import MTNetKeras as MTNetKerasModel
from zoo.automl.model.VanillaLSTM import VanillaLSTM as LSTMKerasModel
from zoo.tfpark import KerasModel as TFParkKerasModel

import functools


class Forecaster(TFParkKerasModel, metaclass=ABCMeta):
    """
    Base class for TFPark KerasModel based Forecast models.
    """
    def __init__(self):
        """
        Initializer.
        Turns the tf.keras model returned from _build into a tfpark.KerasModel
        """
        self.model_ = self._build()
        super().__init__(self.model_)

    @abstractmethod
    def _build(self):
        """
        Build a tf.keras model.
        @param return: return a tf.keras model (compiled)
        """
        pass


class LSTMForecaster(Forecaster):
    """
    Vanilla LSTM Forecaster
    """

    def __init__(self,
                 horizon=1,
                 feature_dim=1,
                 lstm_1_units=16,
                 dropout_1=0.2,
                 lstm_2_units=8,
                 dropout_2=0.2,
                 metric="mean_squared_error",
                 lr=0.001,
                 uncertainty: bool = False
                 ):
        """
        Build a LSTM Forecast Model.

        @param horizon: steps to look forward
        @param feature_dim: dimension of input feature
        @param lstm_1_units: num of units for the 1st LSTM layer
        @param dropout_1: p for the 1st dropout layer
        @param lstm_2_units: num of units for the 2nd LSTM layer
        @param dropout_2: p for the 2nd dropout layer
        @param metric: the metric for validation and evaluation
        @param lr: learning rate
        @param uncertainty: whether to return uncertainty
        """
        #
        self.horizon = horizon
        self.check_optional_config = False
        self.uncertainty = uncertainty
        self.feature_dim = feature_dim

        self.model_config = {
            "lr": lr,
            "lstm_1_units": lstm_1_units,
            "dropout_1": dropout_1,
            "lstm_2_units": lstm_2_units,
            "dropout_2": dropout_2,
            "metric": metric,
        }
        super().__init__()

    def _build(self):
        """
        Build LSTM Model in tf.keras
        """
        # build model with TF/Keras
        internal = LSTMKerasModel(check_optional_config=self.check_optional_config,
                                  future_seq_len=self.horizon)
        # TODO hacking to fix a problem, later set it into model_config
        internal.feature_num = self.feature_dim
        return internal._build(mc=self.uncertainty,
                               **self.model_config)


class MTNetForecaster(Forecaster):
    """
    MTNet Forecast Model
    """
    def __init__(self,
                 horizon=1,
                 feature_dim=1,
                 metric="mean_squared_error",
                 uncertainty: bool = False,
                 ):
        """
        Build a MTNet Forecast Model.
        @param horizon: the steps to look forward
        @param feature_dim: the dimension of input feature
        @param metric: the metric for validation and evaluation
        @param uncertainty: whether to enable calculation of uncertainty
        """
        self.check_optional_config = False
        self.mc = uncertainty
        self.model_config = {
            "feature_num": feature_dim,
            "output_dim": horizon,
            "metrics": [metric],
        }
        self.internal = None

        super().__init__()

    def _build(self):
        """
        build a MTNet model in tf.keras
        @return: a tf.keras MTNet model
        """
        #TODO change this function call after MTNet fixes
        self.internal = MTNetKerasModel(check_optional_config=self.check_optional_config,
                                   future_seq_len=self.model_config.get('horizon'))
        self.internal._get_attributes(mc=self.mc,
                                 metrics=self.model_config.get('metrics'),
                                 epochs=1,
                                 config=self.model_config)
        return self.internal._build_train(mc=self.mc,
                                     metrics=self.model_config.get('metrics'))

    def preprocess_input(self, x):
        """
        The original rolled features needs an extra step to process.
        This should be called before train_x, validation_x, and test_x
        @param x: the original samples from rolling
        @return: a tuple (long_term_x, short_term_x) which are long term and short term history respectively
        """
        return self.internal._gen_hist_inputs(x)