import requests
import json
import sys
import re
import time
import os
from fsm.env.environment_runtime import RuntimeNamespace
from fsm.fsm_fsm import FSM
from fsm.solution import Solution
import subprocess
import unittest
import threading

class http_communication(unittest.TestCase):
    def setUp(self):
        # 在这里初始化测试所需的环境变量
        self.port = "8080"
        self.cpp_server_path = "D:\\me\\华师\\北汽\\代码\\BeiQi_2.0\\Requirement_diagram_analysis.exe"
        self.process = None
    # 唤起c++服务器，成功则返回提示
    def test_call_cpp_server(self):
        try:
            # 启动 C++ 服务器进程
            self.process = subprocess.Popen(
                [
                    self.cpp_server_path,
                    "1",  # 示例参数
                    str(self.port)
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                encoding = 'utf-8'  # 指定编码
            )

            # 打印进程号
            print(f"C++ server started with PID: {self.process.pid}")

            # 实时输出C++服务器日志
            while True:
                # 监控输出
                output = self.process.stdout.readline()
                if output == '' and self.process.poll() is not None:
                    break
                if output:
                    print("C++ Server Output:", output.strip())

            # 检查错误输出
            for error in self.process.stderr:
                print("C++ Server Error:", error.strip())

            # 检查进程是否正常退出
            if self.process.returncode != 0:
                print(f"Error: C++ server exited with code {self.process.returncode}")

        except FileNotFoundError:
            print("Error: Executable not found.")
        except Exception as e:
            print(f"An error occurred: {e}")
        finally:
            # 确保在函数结束时终止 C++ 进程
            if self.process:
                print("Terminating C++ server...")
                self.process.terminate()  # 终止进程
                self.process.wait()  # 等待进程结束
                print("C++ server terminated.")
    # 传递图信息（传递所有图or传递部分图均可）
    def test_send_graph(self):
        solution_path = "..\\demo_分支_环路_输出"
        graph_ids = "5915518c-2c46-11ef-97ca-c8cb9e4ad5d4" # 如果只传递部分图
        env_name = "default"
        database_id = "c263f6cb-c1e3-4f04-a714-fa54b58abbca-default"
        modify_all = True # True代表全部传入，False则只传入graph_ids中的部分
        data = {
            "mode":"a",
            "modify_all":modify_all,  # 添加method字段
            "graphs":[]
        }
        fsm = get_fsm_from_solution(solution_path, env_name, database_id)
        if fsm:
            patterns_blank = {
                '==':' == ',
                '= =':' == ',
                '!=':' != ',
                '<=':' <= ',
                '>=':' >= ',
                '<':' < ',
                '>':' > ',
                '=':' = ',
                '≥':' ≥ ',
                '≤':' ≤ '
            }

            patterns_others = {
                '= =':'=='
            }

            # 预编译正则表达式
            blank_patterns = {re.compile(r'(?<! ){}(?! )'.format(re.escape(pattern))):repl for pattern, repl in
                              patterns_blank.items()}
            other_patterns = {re.compile(re.escape(pattern)):repl for pattern, repl in patterns_others.items()}
            # 确保 graph_ids 是一个列表
            if isinstance(graph_ids, str):
                graph_ids = graph_ids.split(",")  # 将逗号分隔的字符串转换为列表
            if modify_all == False: # 只传入部分
                for graph in fsm.graphs:
                    for graph_id in graph_ids:
                        if graph.id == graph_id:
                            graph_data = {"graph_id":graph.id, "nodes":[], "edges":[]}

                            # 处理节点
                            for node in graph.nodes:
                                node_data = {"node_id":node.id, "node_type":"", "node_information":""}

                                if node.type_name == 'state':  # 是写节点
                                    node_data["node_type"] = "write"
                                    if node.is_init_node:
                                        node_data["node_information"] = "START"
                                    else:
                                        actions = []
                                        for action in node.during_action_list:
                                            modified_str = action.express
                                            for pattern, repl in blank_patterns.items():
                                                modified_str = pattern.sub(repl, modified_str)
                                            for pattern, repl in other_patterns.items():
                                                modified_str = pattern.sub(repl, modified_str)
                                            action.express = modified_str
                                            actions.append(action.express)  # 把表达式存储到列表中
                                        node_data["node_information"] = " and ".join(actions)

                                elif node.type_name == 'condition':  # 是读节点
                                    node_data["node_type"] = "read"
                                    if node.condition != "":
                                        modified_str = node.condition
                                        for pattern, repl in blank_patterns.items():
                                            modified_str = pattern.sub(repl, modified_str)
                                        for pattern, repl in other_patterns.items():
                                            modified_str = pattern.sub(repl, modified_str)
                                        node.condition = modified_str
                                        node_data["branch_yes"] = node.branch_yes
                                        node_data["branch_no"] = node.branch_no
                                        node_data["node_information"] = node.condition

                                graph_data["nodes"].append(node_data)

                            # 处理边
                            for transition in graph.transitions:
                                edge_data = {
                                    "edge_id":transition.id,
                                    "source_node_id":transition.source_node,
                                    "target_node_id":transition.target_node,
                                    "edge_information":""
                                }
                                if transition.condition != "":
                                    modified_str = transition.condition
                                    for pattern, repl in blank_patterns.items():
                                        modified_str = pattern.sub(repl, modified_str)
                                    for pattern, repl in other_patterns.items():
                                        modified_str = pattern.sub(repl, modified_str)
                                    transition.condition = modified_str
                                    edge_data["edge_information"] = transition.condition

                                graph_data["edges"].append(edge_data)

                            data["graphs"].append(graph_data)
            else: # 传入全部图数据
                for graph in fsm.graphs:
                    graph_data = {"graph_id":graph.id, "nodes":[], "edges":[]}

                    # 处理节点
                    for node in graph.nodes:
                        node_data = {"node_id":node.id, "node_type":"", "node_information":""}

                        if node.type_name == 'state':  # 是写节点
                            node_data["node_type"] = "write"
                            if node.is_init_node:
                                node_data["node_information"] = "START"
                            else:
                                actions = []
                                for action in node.during_action_list:
                                    modified_str = action.express
                                    for pattern, repl in blank_patterns.items():
                                        modified_str = pattern.sub(repl, modified_str)
                                    for pattern, repl in other_patterns.items():
                                        modified_str = pattern.sub(repl, modified_str)
                                    action.express = modified_str
                                    actions.append(action.express)  # 把表达式存储到列表中
                                node_data["node_information"] = " and ".join(actions)

                        elif node.type_name == 'condition':  # 是读节点
                            node_data["node_type"] = "read"
                            if node.condition != "":
                                modified_str = node.condition
                                for pattern, repl in blank_patterns.items():
                                    modified_str = pattern.sub(repl, modified_str)
                                for pattern, repl in other_patterns.items():
                                    modified_str = pattern.sub(repl, modified_str)
                                node.condition = modified_str
                                node_data["branch_yes"] = node.branch_yes
                                node_data["branch_no"] = node.branch_no
                                node_data["node_information"] = node.condition

                        graph_data["nodes"].append(node_data)

                    # 处理边
                    for transition in graph.transitions:
                        edge_data = {
                            "edge_id":transition.id,
                            "source_node_id":transition.source_node,
                            "target_node_id":transition.target_node,
                            "edge_information":""
                        }
                        if transition.condition != "":
                            modified_str = transition.condition
                            for pattern, repl in blank_patterns.items():
                                modified_str = pattern.sub(repl, modified_str)
                            for pattern, repl in other_patterns.items():
                                modified_str = pattern.sub(repl, modified_str)
                            transition.condition = modified_str
                            edge_data["edge_information"] = transition.condition

                        graph_data["edges"].append(edge_data)

                    data["graphs"].append(graph_data)
        else:
            print("Fail to create fsm")
        # 要发送的JSON数据
        print(json.dumps(data, indent=4,ensure_ascii=False))  # 格式化输出 JSON 数据

        # 使用 f-string 来动态构建 URL
        url = f"http://localhost:{self.port}/data"
        response = requests.post(url, json=data)

        # 解析并打印响应
        if response.status_code == 200:
            try:
                # 尝试解析返回的 JSON 数据
                json_response = response.json()
                print("Response from C++ server (JSON):", json_response)
            except ValueError:
                # 如果解析失败，说明响应不是 JSON 格式
                print("Response from C++ server (non-JSON):", response.text)
        else:
            print("Failed to connect to the server. Status code:", response.status_code)
    # 请求服务器返回所有依赖关系
    def test_ask_requirements(self):
        data = {
            "mode":"b",
        }
        # 要发送的JSON数据
        print(json.dumps(data, indent=4, ensure_ascii=False))  # 格式化输出 JSON 数据

        # 使用 f-string 来动态构建 URL
        url = f"http://localhost:{self.port}/data"
        response = requests.post(url, json=data)

        # 解析并打印响应
        if response.status_code == 200:
            try:
                # 尝试解析返回的 JSON 数据
                json_response = response.json()
                print("Response from C++ server (JSON):", json_response)
            except ValueError:
                # 如果解析失败，说明响应不是 JSON 格式
                print("Response from C++ server (non-JSON):", response.text)
        else:
            print("Failed to connect to the server. Status code:", response.status_code)
    # 请求服务器返回所有路径信息
    def test_ask_pathdic(self):
        data = {
            "mode":"c",
        }
        # 要发送的JSON数据
        print(json.dumps(data, indent=4, ensure_ascii=False))  # 格式化输出 JSON 数据

        # 使用 f-string 来动态构建 URL
        url = f"http://localhost:{self.port}/data"
        response = requests.post(url, json=data)

        # 解析并打印响应
        if response.status_code == 200:
            try:
                # 尝试解析返回的 JSON 数据
                json_response = response.json()
                print("Response from C++ server (JSON):", json_response)
            except ValueError:
                # 如果解析失败，说明响应不是 JSON 格式
                print("Response from C++ server (non-JSON):", response.text)
        else:
            print("Failed to connect to the server. Status code:", response.status_code)

def get_fsm_from_solution(solution_path, env_name, database_id):
    solution = Solution(solution_path, database_id)
    if not solution.check_valid():
        solution = None
    if solution is None:
        print('Cannot load the solution folder from:' + solution_path)
        return None
    env = solution.env_config.select_env(env_name)
    graphs = solution.get_all_graph_list()
    local_runtime = {}
    env.global_runtime = env.runtime.shallow_copy()
    for graph_item in graphs:
        env.local_runtime[graph_item.id] = RuntimeNamespace()
        local_runtime_item = env.local_runtime[graph_item.id].gen_local_runtime_item(graph_item, env)
        local_runtime[graph_item.id] = local_runtime_item
    env.local_runtime = local_runtime
    if env is None:
        print('Failed to open env:' + env_name)
        return None
    if graphs is None:
        print('Failed to get graph list')
        return None
    return FSM(graphs, env)





