import json
import struct
import math
import time
import random
from sources.base import BaseReader

SHORT = 2
INT16_BYTE_SIZE = 2


class TestReader(BaseReader):
    """ Base Reader Object, describes the methods that must be implemented for each data source"""

    def __init__(self, config, device_id=None, **kwargs):

        super(TestReader, self).__init__(config, device_id, **kwargs)

    @property
    def delay(self):
        return 1.0 / self.sample_rate * self.samples_per_packet / 1.25

    @property
    def byteSize(self):
        if self.config_columns:
            return (
                self.source_samples_per_packet
                * len(self.config_columns)
                * INT16_BYTE_SIZE
            )

        return 0

    def _generate_samples(self, num_columns, sample_rate):
        fs = sample_rate * 10
        f = sample_rate

        x = list(range(0, fs))  # the points on the x axis for plotting

        data =  [
            [
                1000 * offset
                + 1000 * math.sin(2 * math.pi * f * (float(xs * offset * 3.14) / fs))
                for xs in x
            ]
            for offset in range(1, num_columns + 1)
        ]

        sample_data = bytearray(num_columns*len(x)*2)
        for index in x:
            for y in range(0, num_columns):
                struct.pack_into(
                    "<h",
                    sample_data,
                    (y + (index * num_columns)) * 2,
                    int(data[y][index]),
                )

        return bytes(sample_data), len(x)

    def _pack_data(self, data, data_len, num_columns, samples_per_packet, start_index):

        start = start_index*2*num_columns

        if samples_per_packet + start_index > data_len:
            end_index = data_len - (start_index+samples_per_packet)
            end = end_index*2*num_columns

            return data[start:]+data[:end], end_index

        else:
            end_index = start_index+samples_per_packet
            end  = end_index*2*num_columns
            return data[start:end], end_index


    def list_available_devices(self):
        return [
            {"id": 1, "name": "Test Data", "device_id": "Test IMU 6-axis"},
            {"id": 2, "name": "Test Data", "device_id": "Test Audio"},
        ]

    def get_device_info(self):
        pass

    def set_config(self, config):

        if self.device_id == "Test IMU 6-axis":
            config["CONFIG_COLUMNS"] = {
                "AccelerometerX": 0,
                "AccelerometerY": 1,
                "AccelerometerZ": 2,
                "GyroscopeX": 3,
                "GyroscopeY": 4,
                "GyroscopeZ": 5,
            }
            config["CONFIG_SAMPLE_RATE"] = 104
            config["DATA_SOURCE"] = "TEST"
            config["SOURCE_SAMPLES_PER_PACKET"] = 6

        elif self.device_id == "Test Audio":
            config["CONFIG_COLUMNS"] = {
                "Microphone": 0,
            }
            config["CONFIG_SAMPLE_RATE"] = 16000
            config["DATA_SOURCE"] = "TEST"
            config["SOURCE_SAMPLES_PER_PACKET"] = 480

        else:
            raise Exception("Invalid Device ID")

        self.samples_per_packet = config["CONFIG_SAMPLES_PER_PACKET"]
        self.source_samples_per_packet = config["SOURCE_SAMPLES_PER_PACKET"]
        self.sample_rate = config["CONFIG_SAMPLE_RATE"]
        self.config_columns = config.get("CONFIG_COLUMNS")

        config["CONFIG_COLUMNS"] = config.get("CONFIG_COLUMNS")
        config["CONFIG_SAMPLE_RATE"] = config["CONFIG_SAMPLE_RATE"]
        config["DATA_SOURCE"] = "TEST"
        config["SOURCE_SAMPLES_PER_PACKET"] = config["SOURCE_SAMPLES_PER_PACKET"]
        config["TEST_DEVICE"] = self.device_id

    def _read_source(self):
        index = 0
        counter = 0
        buffer_size = 0

        data, data_len = self._generate_samples(len(self.config_columns), self.sample_rate)

        self.streaming = True

        start = time.time()

        sleep_time = self.source_samples_per_packet / float(self.sample_rate)

        cycle = time.time()

        while self.streaming:
            incycle = time.time()
            sample_data, index = self._pack_data(data, data_len, len(self.config_columns), self.source_samples_per_packet, index)
            pack_time = time.time() - incycle
            buffer_time = time.time()
            self.buffer.update_buffer(sample_data)
            buffer_time =  time.time() - buffer_time
            buffer_size += self.source_samples_per_packet
            counter += 1
            incycle = time.time() - incycle

            time.sleep(sleep_time-incycle)

            if time.time() - start > 1:
                start = time.time()
                counter = 0
                buffer_size = 0

            """
            print(
                "total",
                start - time.time(),
                "cycle",
                cycle - time.time(),
                "incycle",
                incycle,
                "buffer",
                buffer_time,
                'pack',
                pack_time,
                "timer",
                sleep_time,
                counter,
                buffer_size,
                len(sample_data),
            )
            """

            cycle = time.time()


class TestResultReader(BaseReader):
    def __init__(self, config, device_id=None, connect=True, **kwargs):

        self.streaming = False

        super(TestResultReader, self).__init__(config, **kwargs)

    def set_config(self, config):
        config["DATA_SOURCE"] = "TEST"

    def _read_source(self):

        self.streaming = True

        while self.streaming:

            self.rbuffer.update_buffer(
                [
                    json.dumps(
                        self._map_classification(
                            {"ModelNumber": 0, "Classification": random.randint(0, 10)}
                        )
                    )
                ]
            )
            time.sleep(0.1)


if __name__ == "__main__":
    config = {
        "CONFIG_SAMPLES_PER_PACKET": 10,
        "CONFIG_SAMPLE_RATE": 100,
        "CONFIG_COLUMNS": ["X", "Y", "Z"],
    }
    t = TestReader(config, "tester")

    t.send_connect()

    s = t.read_data()
    for i in range(5):
        print(next(s))

    t.disconnect()
