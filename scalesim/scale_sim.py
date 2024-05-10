import os
from scale_config import scale_config
from topology_utils import topologies
from simulator import simulator as sim
import pandas as pd
import csv

from memory_map import method_logger


class scalesim:
    @method_logger
    def __init__(self,
                 save_disk_space=False,
                 verbose=True,
                 config='',
                 topology='',
                 input_type_gemm=False):
        # Data structures
        self.config = scale_config()
        self.topo = topologies()

        # File paths
        self.config_file = ''
        self.topology_file = ''

        # Member objects
        #self.runner = r.run_nets()
        self.runner = sim()

        # Flags
        self.read_gemm_inputs = input_type_gemm
        self.save_space = save_disk_space
        self.verbose_flag = verbose
        self.run_done_flag = False
        self.logs_generated_flag = False

        self.set_params(config_filename=config, topology_filename=topology)

    @method_logger
    def set_params(self,
                   config_filename='',
                   topology_filename='' ):
        # First check if the user provided a valid topology file
        if not topology_filename == '':
            if not os.path.exists(topology_filename):
                print("ERROR: scalesim.scale.py: Topology file not found")
                print("Input file:" + topology_filename)
                print('Exiting')
                exit()
            else:
                self.topology_file = topology_filename

        if not os.path.exists(config_filename):
            print("ERROR: scalesim.scale.py: Config file not found") 
            print("Input file:" + config_filename)
            print('Exiting')
            exit()
        else: 
            self.config_file = config_filename

        # Parse config first
        self.config.read_conf_file(self.config_file)

        # Take the CLI topology over the one in config
        # If topology is not passed from CLI take the one from config
        if self.topology_file == '':
            self.topology_file = self.config.get_topology_path()
        else:
            self.config.set_topology_file(self.topology_file)

        # Parse the topology
        self.topo.load_arrays(topofile=self.topology_file, mnk_inputs=self.read_gemm_inputs)

        #num_layers = self.topo.get_num_layers()
        #self.config.scale_memory_maps(num_layers=num_layers)

    @method_logger
    def run_scale(self, top_path='.'):

        self.top_path = top_path
        save_trace = not self.save_space
        self.runner.set_params(
            config_obj=self.config,
            topo_obj=self.topo,
            top_path=self.top_path,
            verbosity=self.verbose_flag,
            save_trace=save_trace
        )
        self.run_once()


        # save finals comparable stats into final.csv
        files = os.listdir(f'./test_runs/{self.config.run_name}')
        for i in range(self.config.memory_banks):
            cols = [self.config_file.split('/')[1], self.topology_file.split('/')[-1], self.config.memory_banks, self.config.ifmap_sz_kb, self.config.df,self.config.use_user_bandwidth]
            bwr = f'BANDWIDTH_REPORT_{i}.csv'
            dar = f'DETAILED_ACCESS_REPORT_{i}.csv' 
            df_bwr = pd.read_csv(f'./test_runs/{self.config.run_name}/{bwr}')
            df_dar = pd.read_csv(f'./test_runs/{self.config.run_name}/{dar}')

            for (index1, row1), (index2, row2) in zip(df_bwr.iterrows(), df_dar.iterrows()):
                # print(row1)
                r = cols.copy()
                r.append(self.config.mapping)
                r.append(row1['LayerID'])
                r.append(i)
                r.append(row2[' DRAM IFMAP Stop Cycle']-row2[' DRAM IFMAP Start Cycle'])
                r.append(row2[' DRAM IFMAP Reads'])
                r.append(row2[' DRAM Filter Stop Cycle']-row2[' DRAM Filter Start Cycle'])
                r.append(row2[' DRAM Filter Reads'])
                r.append(row2[' DRAM OFMAP Stop Cycle']-row2[' DRAM OFMAP Start Cycle'])
                r.append(row2[' DRAM OFMAP Writes'])
                r.append(row1[' Avg IFMAP DRAM BW'])
                r.append(row1[' Avg FILTER DRAM BW'])
                r.append(row1[' Avg OFMAP DRAM BW'])
                
                with open('./test_runs/final.csv', 'a', newline='') as csvfile:
                    # Create a CSV writer object
                    csv_writer = csv.writer(csvfile)
                    
                    # Write the row to the CSV file
                    csv_writer.writerow(r)



    @method_logger
    def run_once(self):

        if self.verbose_flag:
            self.print_run_configs()

        #save_trace = not self.save_space

        # TODO: Anand
        # TODO: This release
        # TODO: Call the class member functions
        #self.runner.run_net(
        #    config=self.config,
        #    topo=self.topo,
        #    top_path=self.top_path,
        #    save_trace=save_trace,
        #    verbosity=self.verbose_flag
        #)
        self.runner.run()
        self.run_done_flag = True

        #self.runner.generate_all_logs()
        self.logs_generated_flag = True

        if self.verbose_flag:
            print("************ SCALE SIM Run Complete ****************")

    @method_logger
    def print_run_configs(self):
        df_string = "Output Stationary"
        df = self.config.get_dataflow()

        if df == 'ws':
            df_string = "Weight Stationary"
        elif df == 'is':
            df_string = "Input Stationary"

        print("====================================================")
        print("******************* SCALE SIM **********************")
        print("====================================================")

        arr_h, arr_w = self.config.get_array_dims()
        print("Array Size: \t" + str(arr_h) + "x" + str(arr_w))

        ifmap_kb, filter_kb, ofmap_kb = self.config.get_mem_sizes()
        print("SRAM IFMAP (kB): \t" + str(ifmap_kb))
        print("SRAM Filter (kB): \t" + str(filter_kb))
        print("SRAM OFMAP (kB): \t" + str(ofmap_kb))
        print("Dataflow: \t" + df_string)
        print("CSV file path: \t" + self.config.get_topology_path())
        print("Number of Remote Memory Banks: \t" + str(self.config.get_mem_banks()))

        if self.config.use_user_dram_bandwidth():
            print("Bandwidth: \t" + self.config.get_bandwidths_as_string())
            print('Working in USE USER BANDWIDTH mode.')
        else:
            print('Working in ESTIMATE BANDWIDTH mode.')

        print("====================================================")

    @method_logger
    def get_total_cycles(self):
        me = 'scale.' + 'get_total_cycles()'
        if not self.run_done_flag:
            message = 'ERROR: ' + me
            message += ' : Cannot determine cycles. Run the simulation first'
            print(message)
            return

        return self.runner.get_total_cycles()
