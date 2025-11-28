# COD_Ch6_Lab2：ISPC 与向量化实验

本项目是 **武汉大学计算机学院《计算机组成与体系结构》课程第六章实验二** 的配套代码。  
实验目标是通过 ISPC 与自定义向量指令接口，体验数据并行程序设计与向量化性能分析。

本次实验包含两个主要任务：

- **任务一：向量指令与掩码（`vecintrin/`）**  
  在给定的向量指令模拟框架上，完成向量化 `clampedExpVector` 和 `arraySumVector`，并完成分析任务。
- **任务二：ISPC 并行开平方（`sqrt/`）**  
  在给定的ISPC框架下，通过调整数据分布使得SIMD得到最佳和最差性能。

---

## 安装 ISPC 编译器（`install_ispc.sh`）

在编译 `sqrt` 任务前，需要先安装 ISPC 编译器。项目根目录下提供自动安装脚本：`install_ispc.sh`。

### 1. 基本用法

在本实验根目录执行：

```bash
chmod +x install_ispc.sh   # 若脚本没有执行权限
./install_ispc.sh
```

脚本会自动完成以下工作：

1. 检查系统中是否安装 `curl` 或 `wget`，用于从 GitHub 下载 ISPC。  
2. 自动探测最新的 ISPC 发布版本（或使用你手动指定的版本）。  
3. 根据当前操作系统与 CPU 架构选择合适的压缩包并下载。  
4. 对下载文件进行基本校验（文件大小、gzip 格式、tar 完整性）。  
5. 将 ISPC 解压到 `~/.local/ispc/bin`，并在 `~/.local/bin` 下创建 `ispc` 软链接。  
6. 在你的 Shell 初始化脚本（`~/.zshrc` 或 `~/.bashrc`）中追加：

   ```bash
   export PATH="$HOME/.local/bin:$PATH"
   ```

安装完成后，按照脚本提示执行：

```bash
source ~/.bashrc  # 或 source ~/.zshrc 取决你使用的shell
ispc --version    # 验证是否安装成功
```


---

## 环境说明

推荐开发/运行环境（Linux / WSL / macOS）：

- C/C++ 编译器：`g++`（支持 C++11 及以上）
- 构建工具：`make`
- Python：`Python 3.8+`
- Python 第三方库：
  - `matplotlib`（用于 `vecintrin/vector_width_sweep.py` 绘图）
- ISPC 编译器：`ispc`（通过 `install_ispc.sh` 安装，或自行安装到 PATH 中）

安装以matplotlib支持Python绘图

```bash
pip install matplotlib
```

---

## 代码结构简要说明

- `install_ispc.sh`  
  自动下载并安装 ISPC 到用户本地目录，并更新 PATH。

- `sqrt/`（任务二：ISPC 并行开平方）
  - `main.cpp`：程序入口，生成不同数据分布，调用串行/ISPC/任务并行版本并计时、验证结果。
  - `sqrtSerial.cpp`：串行开平方实现，用于基准比较。
  - `sqrt.ispc`：ISPC 向量化与任务并行实现，需要在此完成实验内容。
  - `data.cpp`：生成不同分布的数据（random / good / bad）。
  - `Makefile`：使用 `g++` + `ispc` 构建 `sqrt` 可执行文件。

- `vecintrin/`（任务一：向量指令与掩码）
  - `main.cpp`：解析命令行参数，生成测试数据，调用串行与向量化实现并验证正确性，打印统计信息与向量利用率。
  - `functions.cpp`：实验核心，需要实现 `clampedExpVector` 与 `arraySumVector` 的向量化版本。
  - `CMU418intrin.h` / `CMU418intrin.cpp`：提供自定义向量寄存器类型、掩码类型以及一组“向量指令”API（加载、存储、算术、比较、掩码操作等）。
  - `logger.h` / `logger.cpp`：记录向量指令使用情况，最后打印“Vector Utilization”等统计信息。
  - `Makefile`：构建 `vrun` 可执行程序。
  - `vector_width_sweep.py`：Python 脚本，用于自动修改 `VECTOR_WIDTH`、重新编译并运行 `vrun`，统计向量利用率并绘图。


---

## 任务一：向量指令与掩码（`vecintrin/`）

### 1. 编译 `vrun`

在项目根目录执行：

```bash
cd vecintrin
make
```

成功后会在当前目录生成可执行文件：

```bash
./vrun
```

如果需要清理中间文件：

```bash
make clean
```

### 2. 运行 `vrun`

基本用法：

```bash
./vrun
```

常用命令行参数：

- 指定数据规模 `N`：

  ```bash
  ./vrun -s 1024
  # 或
  ./vrun --size 1024
  ```

- 打印向量指令执行日志（调试用）：

  ```bash
  ./vrun -l
  # 或
  ./vrun --log
  ```

- 查看帮助：

  ```bash
  ./vrun -?
  # 或
  ./vrun --help
  ```

程序会对比串行与向量化实现的结果是否一致

### 3. Python 脚本：`vector_width_sweep.py` 使用方法

`vecintrin/vector_width_sweep.py` 用于自动化测试不同 `VECTOR_WIDTH` 下的向量利用率。

#### 基本用法

在 `vecintrin/` 目录下执行：

```bash
cd vecintrin
python3 vector_width_sweep.py
```

默认行为：

- 从 `VECTOR_WIDTH = 2` 扫描到 `32`，步长为 `2`；
- 每个宽度下运行 `./vrun -s 10000`；
- 在当前目录生成：
  - `vector_utilization_results.csv`：记录 `VECTOR_WIDTH` 与对应的利用率；
  - `vector_utilization.png`：绘制“向量宽度 vs 向量利用率”的曲线图（需要安装 `matplotlib`）。

#### 常用参数说明

- `--min-width <N>` / `--max-width <N>` / `--step <N>`  
  控制扫描的 `VECTOR_WIDTH` 范围及步长。例如：

  ```bash
  python3 vector_width_sweep.py --min-width 4 --max-width 32 --step 4
  ```

- `--samples <N>` 或 `-s <N>`  
  每次运行传给 `./vrun` 的样本数量（即 `./vrun -s N`），默认 `10000`：

  ```bash
  python3 vector_width_sweep.py -s 20000
  ```

- `--csv PATH` / `--plot PATH`  
  指定 CSV 与图像的输出路径：

  ```bash
  python3 vector_width_sweep.py --csv out/results.csv --plot out/utilization.png
  ```

- `--skip-plot`  
  只生成 CSV，不绘制图像（无需安装 `matplotlib`）：

  ```bash
  python3 vector_width_sweep.py --skip-plot
  ```

- `--make-jobs N` 或 `-j N`  
  在重新编译时传递 `make -jN` 以加速构建：

  ```bash
  python3 vector_width_sweep.py -j 8
  ```

- `--keep-width`  
  默认情况下脚本会在结束时将 `CMU418intrin.h` 恢复为原始内容；若希望保留最后一次测试的 `VECTOR_WIDTH` 设置，可加入该参数。

- `--verbose`  
  打印每次运行 `./vrun` 的完整输出，便于调试。

使用该脚本可以方便地分析不同向量宽度下的利用率变化趋势，为实验报告中的参数选择与性能讨论提供依据。

---

## 任务二：ISPC 并行开平方（`sqrt/`）

### 1. 编译 `sqrt`

在项目根目录执行：

```bash
cd sqrt
make
```

成功后会在当前目录生成可执行文件：

```bash
./sqrt
```

若需要清理：

```bash
make clean
```

> 注意：
> - 确保已经正确安装 ISPC（可通过 `ispc --version` 检查）。

### 2. 运行 `sqrt`

基本用法：

```bash
./sqrt
```

命令行参数（见 `main.cpp` 中 `usage` 函数）：

- 指定数据分布类型：

  ```bash
  ./sqrt --data r   # random 随机数据（默认）
  ./sqrt --data g   # good 数据
  ./sqrt --data b   # bad 数据
  ```

- 查看帮助信息：

  ```bash
  ./sqrt -?
  # 或
  ./sqrt --help
  ```

通过在不同数据分布下运行程序，可以观察向量化与任务并行对性能的影响，并在实验报告中分析原因。


