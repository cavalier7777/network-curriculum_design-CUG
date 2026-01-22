# 网络可视化指南

本实验（Experiment 6）已集成可视化系统。您可以实时观察网络拓扑、路由表以及数据包流动，并通过 Web 界面下发指令。

## 1. 架构说明

*   **Backend (FastAPI)**: 作为中心控制器，接收各节点的路由表和日志上报，并维护全局网络状态。
*   **Frontend (React)**: 从 Backend 获取数据并渲染拓扑图，提供 Web 终端控制。
*   **Nodes (Experiment 6)**: 启动时自动连接 Backend，上报自身状态并拉取远程指令。

## 2. 启动步骤

请开启三个终端窗口，分别运行以下组件：

### 终端 1: 启动可视化后端

```bash
cd Web-Interface/Backend
# 确保已安装依赖: pip install -r ../../requirements.txt
uvicorn main:app --host 0.0.0.0 --port 8000
```

### 终端 2: 启动可视化前端

```bash
cd Web-Interface/Frontend
# 确保已安装 Node.js 依赖
npm install 
npm run dev
```

*   启动后，浏览器打开显示的地址 (通常是 http://localhost:5173)。

### 终端 3+ : 启动实验节点

您可以启动多个节点 (如 A, B, C)，它们会自动连接到后端。

```bash
python Code_Refactored/Experiment6/network_app.py
```

*   **输入 ID**: 例如 `A`
*   **选择串口**: 选择与其他节点相连的虚拟串口。

## 3. 使用方法

### 查看状态
*   前端页面会自动显示连接的节点（绿色节点）。
*   连线表示节点间的物理/逻辑邻居关系。
*   点击节点或查看右侧日志面板，可以看到实时的路由更新和 Ping/Traceroute 结果。

### 下发指令
在 Web 界面的黑色终端窗口中，您可以直接控制任意节点。

**语法格式**: `<节点ID> <命令>`

**示例**:
*   让节点 A Ping 节点 B:
    `A ping B`
*   让节点 A 追踪节点 C:
    `A tracert C`
*   查看节点 B 的路由表 (本地打印):
    `B table`

### 注意事项
*   如果后端未启动，节点程序仍可正常运行，但会忽略上报错（为了增强鲁棒性）。
*   确保 `Experiment6` 代码中的 `VIZ_SERVER_URL` 指向正确的后端地址 (默认为 `http://localhost:8000/api/report`)。
