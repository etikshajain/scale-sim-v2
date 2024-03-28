# Dummy memory like interface to service the requests of the last level memory
from memory_map import method_logger

class read_port:
    @method_logger
    def __init__(self):
        self.latency = 1

    @method_logger
    def set_params(self, latency):
        self.latency = latency

    @method_logger
    def get_latency(self):
        return self.latency

    # The incoming read requests will be needed when the capability of port is expanded
    # At the moment its kept for compatibility
    @method_logger
    def service_reads(self, incoming_requests_arr_np, incoming_cycles_arr):
        out_cycles_arr = incoming_cycles_arr + self.latency
        return out_cycles_arr
