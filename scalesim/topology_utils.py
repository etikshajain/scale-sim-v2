import math


class topologies(object):
    """
    Class which contains the methods to preprocess the data from topology file (.csv format) before doing compute simulation.
    """

    def __init__(self):
        """
        The constructor method for the class
        """
        self.current_topo_name = ""
        self.topo_file_name = ""
        self.topo_arrays = []
        self.spatio_temp_dim_arrays = []
        self.layers_calculated_hyperparams = []
        self.num_layers = 0
        self.topo_load_flag = False
        self.topo_calc_hyper_param_flag = False
        self.topo_calc_spatiotemp_params_flag = False

    # reset topology parameters
    def reset(self):
        """
        Method to reset the topology parameters.

        :return: None
        """
        print("All data reset")
        self.current_topo_name = ""
        self.topo_file_name = ""
        self.topo_load_flag = False
        self.topo_arrays = []
        self.num_layers = 0
        self.topo_calc_hyper_param_flag = False
        self.layers_calculated_hyperparams = []

    #
    def load_layer_params_from_list(self, layer_name, elems_list=[]):
        """
        Method to load layer parameters from the given layer name and element list.

        :param layer_name: Name of the workload layer
        :param elem_list: List of elements containing dimensions of the workload layer

        :return: None 
        """
        self.topo_file_name = ''
        self.current_toponame = ''
        self.layer_name = layer_name
        self.append_topo_arrays(layer_name, elems_list)

        self.num_layers += 1
        self.topo_load_flag = True

    # Load the topology data from the file
    def load_arrays(self, topofile=""):
        """
        Method to read the topology file and collect names and dimensions of all the workload layers.

        :param topofile: Name of the topology file

        :return: None
        """
        first = True
        self.topo_file_name = topofile.split('/')[-1]
        name_arr = self.topo_file_name.split('.')
        if len(name_arr) > 1:
            self.current_topo_name = self.topo_file_name.split('.')[-2]
        else:
            self.current_topo_name = self.topo_file_name
        f = open(topofile, 'r')
        for row in f:
            row = row.strip()
            if first or row == '':
                first = False
            else:
                elems = row.split(',')[:-1]
                # depth-wise convolution
                if 'DP' in elems[0].strip():
                    for dp_layer in range(int(elems[5].strip())):
                        layer_name = elems[0].strip() + "Channel_" + str(dp_layer)
                        elems[5] = str(1)
                        self.append_topo_arrays(layer_name, elems)
                else:
                    layer_name = elems[0].strip()
                    self.append_topo_arrays(layer_name, elems)

        self.num_layers = len(self.topo_arrays)
        self.topo_load_flag = True

    # Write the contents into a csv file
    def write_topo_file(self,
                      path="",
                      filename=""
                      ):
        """
        Method to write the workload data into a csv file.

        :param path: Location where the csv file is to be stored
        :param filename: Name of the csv file

        :return: None 
        """
        if path == "":
            print("WARNING: topology_utils.write_topo_file: No path specified writing to the cwd")
            path = "./" 

        if filename == "":
            print("ERROR: topology_utils.write_topo_file: No filename provided")
            return

        filename = path + "/" + filename

        if not self.topo_load_flag:
            print("ERROR: topology_utils.write_topo_file: No data loaded")
            return

        header = [
                    "Layer name",
                    "IFMAP height",
                    "IFMAP width",
                    "Filter height",
                    "Filter width",
                    "Channels",
                    "Num filter",
                    "Stride height",
                    "Stride width"
                ]

        f = open(filename, 'w')
        log = ",".join(header)
        log += ",\n"
        f.write(log)

        for param_arr in self.topo_arrays:
            log = ",".join([str(x) for x in param_arr])
            log += ",\n"
            f.write(log)

        f.close()

    # LEGACY
    def append_topo_arrays(self, layer_name, elems):
        """
        Method to append the layer dimensions in int data type and layer name to the topo_arrays variable.
        This method also checks that the filter dimensions do not exceed the ifmap dimensions.

        :param layer_name: Name of the workload layer
        :param elems: List of elements containing dimensions of the workload layer

        :return: None
        """
        entry = [layer_name]

        for i in range(1, len(elems)):
            val = int(str(elems[i]).strip())
            entry.append(val)
            if i == 7 and len(elems) < 9:
                entry.append(val)  # Add the same stride in the col direction automatically

        # ISSUE #9 Fix
        assert entry[3] <= entry[1], 'Filter height cannot be larger than IFMAP height'
        assert entry[4] <= entry[2], 'Filter width cannot be larger than IFMAP width'

        self.topo_arrays.append(entry)

    # create network topology array
    def append_topo_entry_from_list(self, layer_entry_list=[]):
        """
        Method to append the layer dimensions in int data type and layer name.

        :param layer_entry_list: List of elements containing dimensions and name of the workload layer

        :return: None
        """
        assert 7 < len(layer_entry_list) < 10, 'Incorrect number of parameters'

        entry = [str(layer_entry_list[0])]

        for i in range(1, len(layer_entry_list)):
            val = int(str(layer_entry_list[i]).strip())
            entry.append(val)
            if i == 7 and len(layer_entry_list) < 9:
                entry.append(val)           # Add the same stride in the col direction automatically

        self.append_layer_entry(entry,toponame=self.current_topo_name)

    # add to the existing data from a list
    def append_layer_entry(self, entry, toponame=""):
        """
        Method to append data of a single layer to the array containing data of all the layers.
        This method also calls topo_calc_hyperparams method to calculate the hyperparameters.

        :param entry: List containing dimensions(int data type) of the workload layer and its name
        :param toponame: Name of the workload

        :return: None
        """
        assert len(entry) == 9, 'Incorrect number of parameters'

        if not toponame == "":
            self.current_topo_name = toponame

        self.topo_arrays.append(entry)
        self.topo_load_flag = True
        self.topo_calc_hyperparams()
        self.num_layers += 1

    # calculate hyper-parameters (ofmap dimensions, number of MACs, and window size of filter)
    def topo_calc_hyperparams(self, topofilename=""):
        """
        Method to calculate hyper-parameters (ofmap dimensions, number of MACs, and window size of filter) if topology array is loaded.
        
        :param topofilename: Name of the topology file

        :return: None
        """
        if not self.topo_load_flag:
            self.load_arrays(topofilename)
        self.layers_calculated_hyperparams = []
        for array in self.topo_arrays:
            ifmap_h = array[1]
            ifmap_w = array[2]
            filt_h = array[3]
            filt_w = array[4]
            num_ch   = array[5]
            num_filt = array[6]
            stride_h = array[7]
            stride_w = array[8]
            ofmap_h = int(math.ceil((ifmap_h - filt_h + stride_h) / stride_h))
            ofmap_w = int(math.ceil((ifmap_w - filt_w + stride_w) / stride_w))
            num_mac = ofmap_h * ofmap_w * filt_h * filt_w * num_ch * num_filt
            window_size = filt_h * filt_w * num_ch
            entry = [ofmap_h, ofmap_w, num_mac, window_size]
            self.layers_calculated_hyperparams.append(entry)
        self.topo_calc_hyper_param_flag = True

    def calc_spatio_temporal_params(self, df='os', layer_id=0):
        """
        Method to calculate spatio-temporal parameters (S_r, S_c and T) based on the dataflow.
        (Refer the scalesim paper for more info)

        :param df: Name of the dataflow (input, output or weight stationary)
        :param layer_id: Layer number of the workload

        :return: spatio-temporal parameters (S_r, S_c and T)
        """
        s_row = -1
        s_col = -1
        t_time = -1
        if self.topo_calc_hyper_param_flag:
            num_filt  = self.get_layer_num_filters(layer_id= layer_id)
            num_ofmap = self.get_layer_num_ofmap_px(layer_id=layer_id)
            num_ofmap = int(num_ofmap / num_filt)
            window_sz = self.get_layer_window_size(layer_id=layer_id)
            if df == 'os':
                s_row = num_ofmap
                s_col = num_filt
                t_time = window_sz
            elif df == 'ws':
                s_row = window_sz
                s_col = num_filt
                t_time = num_ofmap
            elif df == 'is':
                s_row = window_sz
                s_col = num_ofmap
                t_time = num_filt
        else:
            self.topo_calc_hyperparams(self.topo_file_name)
        return s_row, s_col, t_time

    def set_spatio_temporal_params(self):
        """
        Method to calculate spatio-temporal parameters (S_r, S_c and T) for all the layers

        :return: None
        """
        if not self.topo_calc_hyper_param_flag:
            self.topo_calc_hyperparams(self.topo_file_name)
        for i  in range(self.num_layers):
            this_layer_params_arr = []
            for df in ['os', 'ws', 'is']:
                sr, sc, tt = self.calc_spatio_temporal_params(df=df, layer_id=i)
                this_layer_params_arr.append([sr, sc, tt])
            self.spatio_temp_dim_arrays.append(this_layer_params_arr)
        self.topo_calc_spatiotemp_params_flag = True

    def get_transformed_mnk_dimensions(self):
        """
        Method to get M, N and K parameters for all the layers. 
        These are GEMM parameters in which an input matrix of dimensions MxN is multiplied \
        to a filter matrix of dimensions NxK.

        :return: M, N and K parameters array
        """
        if not self.topo_calc_hyper_param_flag:
            self.topo_calc_hyperparams(self.topo_file_name)

        mnk_dims_arr = []
        for i in range(self.num_layers):
            M = self.get_layer_num_ofmap_px(layer_id=i)
            N = self.get_layer_num_filters(layer_id=i)
            K = self.get_layer_window_size(layer_id=i)

            mnk_dims_arr.append([M, N, K])

        return mnk_dims_arr


    def get_current_topo_name(self):
        """
        Method to get the name of the workload if available. If not, print an error message.

        :return: Name of the workload
        """
        current_topo_name = ""
        if self.topo_load_flag:
            current_topo_name = self.current_topo_name
        else:
            print('Error: get_current_topo_name(): Topo file not read')
        return current_topo_name

    def get_num_layers(self):
        """
        Method to get the number of layers of the workload if available. If not, print an error message.

        :return: Number of layers of the workload
        """
        if not self.topo_load_flag:
            print("ERROR: topologies.get_num_layers: No array loaded")
            return
        return self.num_layers

    #
    def get_layer_ifmap_dims(self, layer_id=0):
        """
        Method to get the ifmap dimensions of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Ifmap height and width
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_ifmap_dims: Invalid layer id")

        layer_params = self.topo_arrays[layer_id]
        return layer_params[1:3]    # Idx = 1, 2

    #
    def get_layer_filter_dims(self, layer_id=0):
        """
        Method to get the filter dimensions of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Filter height and width
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_ifmap_dims: Invalid layer id")

        layer_params = self.topo_arrays[layer_id]
        return layer_params[3:5]    # Idx = 3, 4

    #
    def get_layer_num_filters(self, layer_id=0):
        """
        Method to get the number of filters of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Number of filters
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_num_filter: Invalid layer id")
        layer_params = self.topo_arrays[layer_id]
        return layer_params[6]

    def get_layer_num_channels(self, layer_id=0):
        """
        Method to get the number of channels of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return:Number of channels
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_num_filter: Invalid layer id")
        layer_params = self.topo_arrays[layer_id]
        return layer_params[5]

    #
    def get_layer_strides(self, layer_id=0):
        """
        Method to get the strides of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Strides (both horizontal and vertical) of the convolution
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_strides: Invalid layer id")

        layer_params = self.topo_arrays[layer_id]
        return layer_params[7:9]


    def get_layer_window_size(self, layer_id=0):
        """
        Method to get the convolution window size of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Convolution window size
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_num_filter: Invalid layer id")
        if not self.topo_calc_hyper_param_flag:
            self.topo_calc_hyperparams()
        layer_calc_params = self.layers_calculated_hyperparams[layer_id]
        return layer_calc_params[3]

    def get_layer_num_ofmap_px(self, layer_id=0):
        """
        Method to get the number of ofmap pixels of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Number of ofmap pixels
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_num_filter: Invalid layer id")
        if not self.topo_calc_hyper_param_flag:
            self.topo_calc_hyperparams()
        layer_calc_params = self.layers_calculated_hyperparams[layer_id]
        num_filters = self.get_layer_num_filters(layer_id)
        num_ofmap_px = layer_calc_params[0] * layer_calc_params[1] * num_filters 
        return num_ofmap_px

    def get_layer_ofmap_dims(self, layer_id=0):
        """
        Method to get the ofmap dimensions of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Ofmap height and width
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_ofmap_dims: Invalid layer id")
        if not self.topo_calc_hyper_param_flag:
            self.topo_calc_hyperparams()
        ofmap_dims = self.layers_calculated_hyperparams[layer_id][0:2]
        return ofmap_dims

    def get_layer_params(self, layer_id=0):
        """
        Method to get the parameters of the layer if available. If not, print an error message.

        :param layer_id: Layer number of the workload

        :return: Parameters of the layer
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_params: Invalid layer id")
            return
        layer_params = self.topo_arrays[layer_id]
        return layer_params

    def get_layer_id_from_name(self, layer_name=""):
        """
        Method to get layer number from the given layer name if available. If not, print an error message.

        :param layer_name: Name of the layer

        :return: Layer number of the workload
        """
        if (not self.topo_load_flag) or layer_name == "":
            print("ERROR")
            return
        indx = -1
        for i in range(len(self.topo_arrays)):
            if layer_name == self.topo_arrays[i]:
                indx = i
        if indx == -1:
            print("WARNING: Not found")
        return indx

    #
    def get_layer_name(self, layer_id=0):
        """
        Method to get the layer name from the given layer number if available. If not, print an error message.

        :param layer_name: Layer number of the workload

        :return: Name of the layer
        """
        if not (self.topo_load_flag or self.num_layers - 1 < layer_id):
            print("ERROR: topologies.get_layer_name: Invalid layer id")
            return

        name = self.topo_arrays[layer_id][0]
        return str(name)

    #
    def get_layer_names(self):
        """
        Method to get the names of all the layers in the workload. If not, print an error message.

        :return: Names of all the layers
        """
        if not self.topo_load_flag:
            print("ERROR")
            return
        layer_names = []
        for entry in self.topo_arrays:
            layer_name = str(entry[0])
            layer_names.append(layer_name)
        return layer_names

    def get_layer_mac_ops(self, layer_id=0):
        """
        Method to get the number of mac operations of the layer if hyper-parameters are calculated. If not, \
        calculate the hyper-parameters first.

        :param layer_id: Layer number of the workload

        :return: Number of mac operations of the layer
        """
        if not self.topo_calc_hyper_param_flag:
            self.topo_calc_hyperparams(topofilename=self.topo_file_name)
        layer_hyper_param = self.layers_calculated_hyperparams[layer_id]
        mac_ops = layer_hyper_param[2]
        return mac_ops

    def get_all_mac_ops(self):
        """
        Method to get the total number of mac operations of all the layer if hyper-parameters are calculated. If not, \
        calculate the hyper-parameters first.


        :return: Total number of mac operations of all the layers
        """
        if not self.topo_calc_hyper_param_flag:
            self.topo_calc_hyperparams(topofilename=self.topo_file_name)
        total_mac = 0
        for layer in range(self.num_layers):
            total_mac += self.get_layer_mac_ops(layer)
        return total_mac

    # spatio-temporal dimensions specific to dataflow
    def get_spatiotemporal_dims(self, layer_id=0, df=''):
        """
        Method to get the spatio-temporal dimensions (S_r, S_c, T) of the layer if spatio-temporal parameters are calculated. If not, \
        calculate the spatio-temporal parameters first.
        (refer to the scalesim paper for more info)

        :param layer_id: Layer number of the workload
        :param df: Name of the dataflow (input, output or weight stationary)

        :return: Spatio-temporal dimensions of the layer (S_r, S_c, T)
        """
        if df == '':
            df = self.df
        if not self.topo_calc_spatiotemp_params_flag:
            self.set_spatio_temporal_params()
        df_list = ['os', 'ws', 'is']
        df_idx = df_list.index(df)
        s_row = self.spatio_temp_dim_arrays[layer_id][df_idx][0]
        s_col = self.spatio_temp_dim_arrays[layer_id][df_idx][1]
        t_time = self.spatio_temp_dim_arrays[layer_id][df_idx][2]
        return s_row, s_col, t_time


if __name__ == '__main__':
    tp = topologies()
