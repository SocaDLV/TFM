#include "module/communication.h"
#include "scheduler/scheduler.h"
#include "common/assert.h"

// --- INICIO CÓDIGO TFM: ORÁCULO DE BOOKSIM2 ---
#include <map>
#include <vector>
#include <string>
#include <unordered_set>

#include "booksim_api.hpp"

class BookSimCoSimManager {
public:
    static std::map<std::string, int> calls_per_module;
    static std::map<std::string, double> cached_latency;
    static int total_injected;
    static int total_received;
    static bool initialized;

    static void Init() {
        if (!initialized) {
            BookSim_Initialize("test.cfg"); 
            initialized = true;
            total_injected = 0;
            total_received = 0;
        }
    }
};

std::map<std::string, int> BookSimCoSimManager::calls_per_module;
std::map<std::string, double> BookSimCoSimManager::cached_latency;
int BookSimCoSimManager::total_injected = 0;
int BookSimCoSimManager::total_received = 0;
bool BookSimCoSimManager::initialized = false;
// --- FIN CÓDIGO TFM ---

namespace llm_system {

AllReduce::AllReduce(std::string& prefix, std::string& name,
                     std::vector<int> device_list, Device::Ptr device)
    : Module(prefix, name, device, device_list, true, true) { 
  std::vector<int> shape = {1, 1};
  Tensor::Ptr output = Tensor::Create("allreduce_output", shape, "act", device, device->model_config.precision_byte);
  add_tensor(output);
}

Tensor::Ptr AllReduce::forward(const Tensor::Ptr input,
                               BatchedSequence::Ptr sequences_metadata) {
  int m = input->shape[0];
  int k = input->shape[1];

  Tensor::Ptr output = get_activation("allreduce_output", input->shape);

  long size = input->getSize();
  if (size == 0) {
    return output;
  }

  int hop = (device_list.size() - 1) * 2;
  size /= device_list.size();

  time_ns one_hop =
      device->config.device_ict_latency +
      size / device->config.device_ict_bandwidth * 1000 * 1000 * 1000;

  time_ns total_time = one_hop * hop;

  time_ns start_time = device->status.device_time;

  if (input->parallel_execution && !device->config.communication_hiding) {
    if (input->isPerformHigh()) {
      device->status.high_time += total_time;
    } else {
      device->status.low_time += total_time;
    }
  }
  device->status.device_time += total_time;
  time_ns end_time = device->status.device_time;

  if (total_time > 0) {
    std::string details = "ProcType:3|Comp_ns:0.000000|Mem_ns:" + std::to_string(total_time);
    device->log_tfm_event(start_time, end_time, this->name, details);
  }

  return output;

}

AllGather::AllGather(std::string& prefix, std::string& name,
                     std::vector<int> device_list, Device::Ptr device)
    : Module(prefix, name, device, device_list, true, true) {
  std::vector<int> shape = {1, 1};
  Tensor::Ptr output = Tensor::Create("allgather_output", shape, "act", device, device->model_config.precision_byte);
  add_tensor(output);
}

Tensor::Ptr AllGather::forward(const Tensor::Ptr input,
                               BatchedSequence::Ptr sequences_metadata) {
  Tensor::Ptr output = get_activation("allgather_output", input->shape);
  return output;
}

AllScatter::AllScatter(std::string& prefix, std::string& name,
                     std::vector<int> device_list, Device::Ptr device)
    : Module(prefix, name, device, device_list, true, true) {
  std::vector<int> shape = {1, 1};
  parallel_num = device_list.size();
  Tensor::Ptr output = Tensor::Create("allscatter_output", shape, "act", device, device->model_config.precision_byte);
  add_tensor(output);
}

Tensor::Ptr AllScatter::forward(const Tensor::Ptr input,
                                BatchedSequence::Ptr sequences_metadata) {
  std::vector<int> shape = {input->shape[0], input->shape[1] / parallel_num};
  Tensor::Ptr output = get_activation("allscatter_output", shape);
  return output;
}

MoEScatter::MoEScatter(std::string& prefix, std::string& name,
                       std::vector<int> device_list, Device::Ptr device)
    : Module(prefix, name, device, device_list, true, true) {
  std::vector<int> shape = {1, 1};
  Tensor::Ptr output = Tensor::Create("moe_scatter_output", shape, "act", device, device->model_config.precision_byte);
  add_tensor(output);
}

Tensor::Ptr MoEScatter::forward(const Tensor::Ptr input,
                                BatchedSequence::Ptr sequences_metadata) {
  int k = input->shape[1];
  Tensor::Ptr output = get_activation("moe_scatter_output", input->shape);

  if (!device->perform_execution) {
    return output;
  }

  BookSimCoSimManager::Init();

  int total_num_device = device->config.num_device * device->config.num_node;
  int ne_tp_dg = device->model_config.ne_tp_dg;
  int e_tp_dg = device->model_config.e_tp_dg;
  std::string layer_name = this->name;
  double network_latency_ns = 0.0;

  // --- INICIO CÓDIGO TFM: ORÁCULO SCATTER ---
  if (BookSimCoSimManager::calls_per_module[layer_name] == 0) {
      // Somos la GPU 0 en llegar. Predecimos el tráfico de todo el clúster.
      int MTU = 256;          
      int HEADER_SIZE = 24;   
      int FLIT_SIZE = 32;     

      for(int src = 0; src < total_num_device; src++) {
          int src_dp_idx = src / ne_tp_dg;
          std::vector<int> tp_sharing_device_list = {};
          int device_list_offset = src / ne_tp_dg * ne_tp_dg;
          for(int device_idx = device_list_offset; device_idx < device_list_offset + ne_tp_dg; device_idx++){
            tp_sharing_device_list.push_back(device_idx);
          }
          std::unordered_set<int> set_tp_devices(tp_sharing_device_list.begin(), tp_sharing_device_list.end());

          for(int dst = 0; dst < total_num_device; dst++) {
              if(set_tp_devices.count(dst) == 0 && src != dst) {
                  int expert_id_offset = device->model_config.num_routed_expert / total_num_device * (dst / e_tp_dg) * e_tp_dg;
                  int num_expert_per_device = device->model_config.num_routed_expert / total_num_device * e_tp_dg;
                  
                  int tokens_to_dst = 0;
                  for(int e_id = expert_id_offset; e_id < expert_id_offset + num_expert_per_device; e_id++) {
                      tokens_to_dst += sequences_metadata->scheduler->running_queue[src_dp_idx]->local_num_token_in_expert[e_id];
                  }

                  long bytes_to_dst = (long)tokens_to_dst * k * input->precision_byte / ne_tp_dg;

                  if (bytes_to_dst > 0) {
                      int num_packets = (bytes_to_dst + MTU - 1) / MTU;
                      for (int p = 0; p < num_packets; p++) {
                          long payload = (p == num_packets - 1) ? (bytes_to_dst % MTU) : MTU;
                          if (payload == 0) payload = MTU;
                          int flits = (payload + HEADER_SIZE + FLIT_SIZE - 1) / FLIT_SIZE;
                          
                          BookSim_InjectPacket(src, dst, flits);
                          BookSimCoSimManager::total_injected++;
                      }
                  }
              }
          }
      }

      // Simulamos toda la capa en BookSim2 de golpe
      int cycles = 0;
      BookSimPacketInfo pkt_info;
      while(BookSimCoSimManager::total_received < BookSimCoSimManager::total_injected) {
          BookSim_AdvanceCycle();
          cycles++;
          while(BookSim_CheckReceived(pkt_info)) { 
              BookSimCoSimManager::total_received++;
          }
      }

      // Guardamos el resultado en caché (1 ciclo = 1 ns)
      BookSimCoSimManager::cached_latency[layer_name] = cycles * 1.0;
  }

  // Todas las GPUs (incluida la 0) leen la caché
  network_latency_ns = BookSimCoSimManager::cached_latency[layer_name];

  // Aplicar latencia al reloj. Esto se guardará de forma NATIVA en el .trc
  if (input->parallel_execution && !device->config.communication_hiding) {
    if (input->isPerformHigh()) {
      device->status.high_time += network_latency_ns;
    } else {
      device->status.low_time += network_latency_ns;
    }
  }
  device->status.device_time += network_latency_ns;

  // --- INICIO AÑADIDO PARA LOGGER ---
  time_ns start_time = device->status.device_time - network_latency_ns;
  time_ns end_time = device->status.device_time;
  std::string details = "ProcType:3|Comp_ns:0.000000|Mem_ns:" + std::to_string(network_latency_ns);
  device->log_tfm_event(start_time, end_time, layer_name, details);
  // --- FIN AÑADIDO PARA LOGGER ---

  // Gestionar el ciclo de vida del Oráculo
  BookSimCoSimManager::calls_per_module[layer_name]++;
  if (BookSimCoSimManager::calls_per_module[layer_name] == total_num_device) {
      BookSimCoSimManager::calls_per_module[layer_name] = 0;
      BookSimCoSimManager::cached_latency.erase(layer_name);
      BookSimCoSimManager::total_injected = 0;
      BookSimCoSimManager::total_received = 0;
  }
  // --- FIN CÓDIGO TFM ---

  return output;
}

MoEGather::MoEGather(std::string& prefix, std::string& name,
                     std::vector<int> device_list, Device::Ptr device)
    : Module(prefix, name, device, device_list, true) {
  std::vector<int> shape = {1, 1};
  Tensor::Ptr output = Tensor::Create("moe_gather_output", shape, "act", device, device->model_config.precision_byte);
  add_tensor(output);
}

TensorVec MoEGather::forward(const TensorVec input_vec,
                             BatchedSequence::Ptr sequences_metadata) {
  Tensor::Ptr input = input_vec.at(0);
  int k = input->shape[1];
  
  if (!device->perform_execution) {
    return input_vec;
  }

  int e_tp_dg = device->model_config.e_tp_dg;
  int ne_tp_dg = device->model_config.ne_tp_dg;
  int total_num_device = device->config.num_device * device->config.num_node;
  std::string layer_name = this->name;
  double network_latency_ns = 0.0;

  // --- INICIO CÓDIGO TFM: ORÁCULO GATHER ---
  if (BookSimCoSimManager::calls_per_module[layer_name] == 0) {
      int MTU = 256;          
      int HEADER_SIZE = 24;   
      int FLIT_SIZE = 32;     

      for(int dst = 0; dst < total_num_device; dst++) {
          int dst_dp_idx = dst / ne_tp_dg;
          std::vector<int> e_tp_sharing_device_list = {};
          int device_list_offset = dst / e_tp_dg * e_tp_dg;
          for(int device_idx = device_list_offset; device_idx < device_list_offset + e_tp_dg; device_idx++){
            e_tp_sharing_device_list.push_back(device_idx);
          }
          std::unordered_set<int> set_e_tp_devices(e_tp_sharing_device_list.begin(), e_tp_sharing_device_list.end());

          for(int src = 0; src < total_num_device; src++) {
              if(set_e_tp_devices.count(src) == 0 && src != dst) { 
                  int expert_id_offset = device->model_config.num_routed_expert / total_num_device * (src / e_tp_dg) * e_tp_dg;
                  int num_expert_per_device = device->model_config.num_routed_expert / total_num_device * e_tp_dg;

                  int tokens_from_src = 0;
                  for(int e_id = expert_id_offset; e_id < expert_id_offset + num_expert_per_device; e_id++){
                    tokens_from_src += sequences_metadata->scheduler->running_queue[dst_dp_idx]->local_num_token_in_expert[e_id];
                  }

                  long bytes_from_src = 1.0 * tokens_from_src * k * input->precision_byte / e_tp_dg / ne_tp_dg;

                  if ((device->model_config.model_name == "deepseekV3") && device->model_config.precision_byte == 1){
                    bytes_from_src *= 2;
                  }

                  if (bytes_from_src > 0) {
                      int num_packets = (bytes_from_src + MTU - 1) / MTU;
                      for (int p = 0; p < num_packets; p++) {
                          long payload = (p == num_packets - 1) ? (bytes_from_src % MTU) : MTU;
                          if (payload == 0) payload = MTU;
                          int flits = (payload + HEADER_SIZE + FLIT_SIZE - 1) / FLIT_SIZE;
                          
                          BookSim_InjectPacket(src, dst, flits);
                          BookSimCoSimManager::total_injected++;
                      }
                  }
              }
          }
      }

      int cycles = 0;
      BookSimPacketInfo pkt_info;
      while(BookSimCoSimManager::total_received < BookSimCoSimManager::total_injected) {
          BookSim_AdvanceCycle();
          cycles++;
          while(BookSim_CheckReceived(pkt_info)) {
              BookSimCoSimManager::total_received++;
          }
      }

      BookSimCoSimManager::cached_latency[layer_name] = cycles * 1.0;
  }

  network_latency_ns = BookSimCoSimManager::cached_latency[layer_name];

  if (input->parallel_execution && !device->config.communication_hiding) {
    if (input->isPerformHigh()) {
      device->status.high_time += network_latency_ns;
    } else {
      device->status.low_time += network_latency_ns;
    }
  }
  device->status.device_time += network_latency_ns;

  // --- INICIO AÑADIDO PARA LOGGER ---
  time_ns start_time = device->status.device_time - network_latency_ns;
  time_ns end_time = device->status.device_time;
  std::string details = "ProcType:3|Comp_ns:0.000000|Mem_ns:" + std::to_string(network_latency_ns);
  device->log_tfm_event(start_time, end_time, layer_name, details);
  // --- FIN AÑADIDO PARA LOGGER ---

  BookSimCoSimManager::calls_per_module[layer_name]++;
  if (BookSimCoSimManager::calls_per_module[layer_name] == total_num_device) {
      BookSimCoSimManager::calls_per_module[layer_name] = 0;
      BookSimCoSimManager::cached_latency.erase(layer_name);
      BookSimCoSimManager::total_injected = 0;
      BookSimCoSimManager::total_received = 0;
  }
  // --- FIN CÓDIGO TFM ---

  return input_vec;
}

Sync::Sync(std::string& prefix, std::string& name, std::vector<int> device_list,
           Device::Ptr device)
    : Module(prefix, name, device, device_list) {
  auto sync__set = Sync__Set::Create(module_map_name, "sync__set", device_list, device);
  add_module(sync__set);
  auto sync__ = Sync__::Create(module_map_name, "sync__", device_list, device);
  add_module(sync__);
}

Tensor::Ptr Sync::forward(const Tensor::Ptr input,
                          BatchedSequence::Ptr sequences_metadata) {
  auto sync__set = get_module("sync__set");
  auto sync__ = get_module("sync__");

  Tensor::Ptr temp = (*sync__set)(input, sequences_metadata);
  Tensor::Ptr output = (*sync__)(temp, sequences_metadata);
  return output;
}

Sync__Set::Sync__Set(std::string& prefix, std::string& name,
                     std::vector<int> device_list, Device::Ptr device)
    : Module(prefix, name, device, device_list, true) {
  std::vector<int> shape = {1, 1};
  Tensor::Ptr output = Tensor::Create("sync", shape, "act", device, device->model_config.precision_byte);
  add_tensor(output);
}

Tensor::Ptr Sync__Set::forward(const Tensor::Ptr input,
                               BatchedSequence::Ptr sequences_metadata) {
  Tensor::Ptr output = get_activation("sync");
  device->status.device_time =
      std::max(device->status.device_time,
               std::max(device->status.low_time, device->status.high_time));
  device->status.high_time = device->status.device_time;
  device->status.low_time = device->status.device_time;
  return output;
}

Sync__::Sync__(std::string& prefix, std::string& name,
               std::vector<int> device_list, Device::Ptr device)
    : Module(prefix, name, device, device_list, true, true) {}

Tensor::Ptr Sync__::forward(const Tensor::Ptr input,
                            BatchedSequence::Ptr sequences_metadata) {
  return input;
}

}  // namespace llm_system