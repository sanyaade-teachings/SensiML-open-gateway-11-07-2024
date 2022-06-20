import json
import threading
import struct
import time
import csv
import os
import random
from open_gateway.sources.utils.sml_runner import SMLRunner
from open_gateway import basedir, ensure_folder_exists
import random

try:
    from open_gateway.sources.buffers import (
        CircularBufferQueue,
        CircularResultsBufferQueue,
    )
except:
    from open_gateway.buffers import CircularBufferQueue, CircularResultsBufferQueue


class BaseReader(object):
    """ Base Reader Object, describes the methods that must be implemented for each data source"""

    def __init__(self, config, device_id=None, name=None, **kwargs):
        self.samples_per_packet = config["CONFIG_SAMPLES_PER_PACKET"]
        self.class_map = config["CLASS_MAP"]
        self.model_json = config["MODEL_JSON"]
        self.loop = config["LOOP"]
        self.source_samples_per_packet = None
        self.data_type = config.get("DATA_TYPE", "int16")
        self.sml_library_path = config.get("SML_LIBRARY_PATH", None)
        self.run_sml_model = config.get("RUN_SML_MODEL", False)
        self.convert_to_int16 = config.get("CONVERT_TO_INT16", False)
        self.scaling_factor = config.get("SCALING_FACTOR", 1)
        self.sml = None
        self.sample_rate = None
        self.config_columns = None
        self.device_id = device_id
        self.recording = False
        self.streaming = False
        self._thread = None
        self._record_thread = None
        self.buffer = None
        self.rbuffer = None
        self._lock = threading.Lock()

    @property
    def data_width(self):
        if self.config_columns is None:
            return 0

        return len(self.config_columns)

    @property
    def data_byte_size(self):

        INT16_BYTE_SIZE = 2
        FLOAT32_BYTE_SIZE = 4

        if self.data_type == "int16":
            return INT16_BYTE_SIZE
        elif self.data_type == "float":
            return FLOAT32_BYTE_SIZE

        return INT16_BYTE_SIZE

    @property
    def data_type_str(self):
        if self.data_type == "int16":
            return "h"
        elif self.data_type == "float":
            return "f"

        return INT16_BYTE_SIZE

    @property
    def data_type_cast(self):
        if self.data_type == "int16":
            return int
        elif self.data_type == "float":
            return float

        return int

    @property
    def data_width_bytes(self):

        return self.data_width * self.data_byte_size

    @property
    def packet_buffer_size(self):
        return self.samples_per_packet * self.source_buffer_size

    @property
    def source_buffer_size(self):
        if self.source_samples_per_packet is None:
            return self.data_byte_size
        return self.source_samples_per_packet * self.data_width_bytes

    @staticmethod
    def _validate_config(config):

        if not isinstance(config, dict):
            raise Exception("Invalid Configuration")

        if config.get("column_location", None) is None:
            raise Exception("Invalid Configuration: no column_location")
        if config.get("sample_rate", None) is None:
            raise Exception("Invalid Configuration: no sample_rate")
        if config.get("samples_per_packet", None) is None:
            raise Exception("Invalid Configuration: no samples_per_packet")

        print("Found configuration:", config)

        return config

    @staticmethod
    def _validate_results_data(data):
        if not data:
            return False
        else:
            try:
                tmp = json.loads(data)
                if isinstance(tmp, dict) and tmp:
                    return True

            except Exception as e:
                print(e)

        return False

    def is_recording(self):
        return self.recording

    def is_streaming(self):
        return self.streaming

    def list_available_devices(self):
        return []

    def _send_subscribe(self):
        pass

    def read_config(self):
        """ read the config from the device and set the properties of the object """

        print("Reader: reading device config")
        config = self.read_device_config()

        self.source_samples_per_packet = config.get("samples_per_packet", None)
        self.sample_rate = config.get("sample_rate", None)
        self.config_columns = config.get("column_location", None)
        self.data_type = config.get("data_type", "int16")

        return config

    def set_app_config(self, config):
        config["DATA_SOURCE"] = self.name
        config["CONFIG_COLUMNS"] = self.config_columns
        config["CONFIG_SAMPLE_RATE"] = self.sample_rate
        config["SOURCE_SAMPLES_PER_PACKET"] = self.source_samples_per_packet
        config["DEVICE_ID"] = self.device_id
        config["DATA_TYPE"] = self.data_type

    def update_config(self, config):
        """ update the objects local config values from the app cache """

        self.samples_per_packet = config["CONFIG_SAMPLES_PER_PACKET"]
        self.source_samples_per_packet = config["SOURCE_SAMPLES_PER_PACKET"]
        self.sample_rate = config["CONFIG_SAMPLE_RATE"]
        self.config_columns = config.get("CONFIG_COLUMNS")
        self.class_map = config.get("CLASS_MAP")
        self.data_type = config.get("DATA_TYPE", "int16")

    def connect(self):

        if self._thread is None:
            "Assume if there is a thread, we are already connected"

            self.buffer = CircularBufferQueue(
                self._lock, buffer_size=self.packet_buffer_size
            )
            self.rbuffer = CircularResultsBufferQueue(self._lock, buffer_size=1)

            print("Base: Sending subscribe to source")
            self._send_subscribe()

            time.sleep(1)

            self.buffer.reset_buffer()

            print("Base: Setting up thread to read source")

            self._thread = threading.Thread(target=self._read_source)
            self._thread.start()

            time.sleep(1)

        else:
            print("Base: Thread Already Started!")

    def disconnect(self):
        self.streaming = False
        self._thread = None
        self._record_thread = None
        self.recording = False

        self.buffer.reset_buffer()
        self.rbuffer.reset_buffer()

    def record_start(self, filename):

        if not self.streaming:
            raise Exception("Must start streaming before beginning to record!")

        if self.recording:
            raise Exception("Only a single recording can occur at one time")

        if filename is None:
            raise Exception("Invalid Filename")

        if not os.path.exists(os.path.dirname(filename)):
            print(
                "Base: File directory does not exist, recording to data directory in gateway location."
            )
            ensure_folder_exists("data")

            filename = os.path.join(basedir, "data", os.path.basename(filename))

        self.recording = True
        self._record_thread = threading.Thread(
            target=self._record_data, kwargs={"filename": filename}
        )
        self._record_thread.start()

    def record_stop(self, filename=None):
        if self.recording != True:
            raise Exception("Not currently recording")

        self._record_thread = None
        self.recording = False

        return True

    def convert_data_to_list(self, data):

        num_samples = len(data) // self.data_byte_size

        tmp = struct.unpack(self.data_type_str * num_samples, data)

        tmp = [x * self.scaling_factor for x in tmp]

        for index in range(self.source_samples_per_packet):
            yield tmp[index * self.data_width : (index + 1) * self.data_width]

    def convert_data_to_int16(self, data):

        num_samples = len(data) // self.data_byte_size

        tmp = struct.unpack(self.data_type_str * num_samples, data)

        sample_data = bytearray(num_samples * 2)

        for index in range(num_samples):
            # print(tmp[index])

            struct.pack_into(
                "<" + "h", sample_data, index * 2, int(tmp[index] * self.scaling_factor)
            )

        return bytes(sample_data)

    def get_sml_model_obj(self):

        sml = SMLRunner(os.path.join(self.sml_library_path))
        sml.init_model()
        print("Model initialized")

        return sml

    def execute_run_sml_model(self, sml, data):
        for data_chunk in self.convert_data_to_list(data):
            ret = sml.run_model(data_chunk, 0)
            if ret >= 0:
                print(
                    self._map_classification({"ModelNumber": 0, "Classification": ret})
                )
                sml.reset_model(0)
                return  self._map_classification({"ModelNumber": 0, "Classification": ret})
            

    def _map_classification(self, results):
        if self.model_json:
            results["Classification"] = self.model_json["ModelDescriptions"][
                results["ModelNumber"]
            ]["ClassMaps"][str(results["Classification"])]

        elif self.class_map:
            results["Classification"] = self.class_map.get(
                results["Classification"], results["Classification"]
            )

        return results


class BaseStreamReaderMixin(object):

    def read_result_data(self):
        print("StreamReader: New stream reader connected")
        # name = random.randint(0, 100)

        if self._thread:
            pass
        else:
            print("StreamReader: establishing a connection to the device.")
            self.connect()
            self.streaming = True

        index = self.rbuffer.get_latest_buffer()

        rand = random.randint(0, 100)

        while self.streaming:

            if index is None:
                index = self.rbuffer.get_latest_buffer()
                time.sleep(0.1)
                continue

            if self.rbuffer.is_buffer_full(index):
                data = self.rbuffer.read_buffer(index)
                index = self.rbuffer.get_next_index(index)

                for result in data:
                    if result:                      
                        result["timestamp"] = time.time()
                        print('reader', index, result)
                        yield json.dumps(result) + "\n"

            else:
                time.sleep(0.1)

        print("ResultReader: Result stream ended")

    def read_data(self):
        """ Generator to read the data stream out of the buffer """

        print("StreamReader: New stream reader connected")
        # name = random.randint(0, 100)

        if self._thread:
            pass
        else:
            print("StreamReader: establishing a connection to the device.")
            self.connect()
            self.streaming = True

        index = self.buffer.get_latest_buffer()

        while self.streaming:

            if index is None:
                index = self.buffer.get_latest_buffer()
                time.sleep(0.1)
                continue

            if self.buffer.is_buffer_full(index):
                data = self.buffer.read_buffer(index)
                index = self.buffer.get_next_index(index)

                if self.convert_to_int16 and self.data_type_str == "f":
                    data = self.convert_data_to_int16(data)

                if data:
                    yield data

            time.sleep(0.001)

        print("StreamReader: Stream Ended")

    def _record_data(self, filename):

        with open(filename + ".csv", "w", newline="") as csvfile:
            datawriter = csv.writer(csvfile, delimiter=",")
            print("StreamReader: Recording stream to ", filename + ".csv")

            datawriter.writerow(
                [
                    x[0]
                    for x in sorted(
                        self.config_columns.items(), key=lambda item: item[1]
                    )
                ]
            )
            struct_info = self.data_type_str * self.data_width

            data_reader = self.read_data()

            while self.recording:

                data = next(data_reader)

                if data:
                    for row_index in range(len(data) // (self.data_width_bytes)):
                        buff_index = row_index * self.data_width_bytes
                        datawriter.writerow(
                            struct.unpack(
                                struct_info,
                                data[buff_index : buff_index + self.data_width_bytes],
                            )
                        )

        print("StreamReader: CSV recording thread finished")


class BaseResultReaderMixin(object):
    def read_device_config(self):
        print("ResultReader: reading device config")
        return {"samples_per_packet": 1}

    def read_data(self):
        """ Generator to read the result stream out of the buffer """

        print("ResultReader: result read starting")

        if self._thread:
            pass
        else:
            print("sent connect")
            self.connect()

        index = self.rbuffer.get_latest_buffer()

        rand = random.randint(0, 100)

        while self.streaming:

            if index is None:
                index = self.rbuffer.get_latest_buffer()
                time.sleep(0.1)
                continue

            if self.rbuffer.is_buffer_full(index):
                data = self.rbuffer.read_buffer(index)
                index = self.rbuffer.get_next_index(index)

                for result in data:
                    if self._validate_results_data(result):
                        try:
                            result = json.loads(result)
                        except Exception as e:
                            print("ResultReader: Failed to read result as a json.")
                            print(result)
                            print(e)
                            continue
                        try:
                            result = self._map_classification(result)
                        except Exception as e:
                            print("ResultReader: Failed map the classification.")
                            print(result)
                            print(e)
                            continue
                        result["timestamp"] = time.time()
                        print(index, result)
                        yield json.dumps(result) + "\n"

            else:
                time.sleep(0.1)

        print("ResultReader: Result stream ended")

    def read_result_data(self):
        return self.read_data()


    def _record_data(self, filename):

        with open(filename + ".csv", "w", newline="") as out:
            print("ResultReader: Recording results to ", filename + ".csv")
            data_reader = self.read_data()

            while self.recording:

                data = next(data_reader)

                if data:
                    out.write(data)

        print("ResultReader: Recording data finished")
