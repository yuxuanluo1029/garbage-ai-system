# Linux 训练包

这个训练包用于在 Linux 服务器上训练 4 类垃圾检测 YOLO 模型。

## 你需要上传到服务器的内容

1. 这个训练包目录 `linux_train_pack/`
2. 你的数据集目录，例如：

```text
/data/garbage_dataset/
├─ images/
└─ labels/
   ├─ classes.txt
   └─ *.txt
```

当前数据集类别文件 `classes.txt` 内容应为：

```text
recyclable waste
hazardous waste
kitchen waste
other waste
```

## 建议的服务器目录结构

```text
/workspace/garbage_train/
├─ linux_train_pack/
└─ garbage_dataset/
   ├─ images/
   └─ labels/
```

## 环境准备

### 方式 1：conda

```bash
conda create -n garbage-yolo python=3.10 -y
conda activate garbage-yolo
pip install -r requirements-train.txt
```

### 方式 2：venv

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install --upgrade pip
pip install -r requirements-train.txt
```

如果你的服务器没有预装 GPU 版 PyTorch，请先按你机器的 CUDA 版本安装官方对应的 `torch`、`torchvision`。

## 一键训练

进入训练包目录后执行：

```bash
chmod +x run_train.sh
./run_train.sh /workspace/garbage_train/garbage_dataset /workspace/garbage_train/workdir
```

默认参数：

- 基础模型：`yolov8s.pt`
- 训练轮数：`50`
- 图片尺寸：`640`
- batch：`16`
- workers：`8`
- device：`0`

如果显存不够，可以改小：

```bash
EPOCHS=30 BATCH=8 WORKERS=4 ./run_train.sh /workspace/garbage_train/garbage_dataset /workspace/garbage_train/workdir
```

## 训练输出

训练完成后，权重一般会在：

```text
/workspace/garbage_train/workdir/runs/garbage4_yolov8s/weights/best.pt
```

你只需要把这个 `best.pt` 下载回来，然后在网页项目里把：

```env
VISION_MODEL_PATH=best.pt 的实际路径
```

改成这个训练好的权重即可。

## 分步命令

如果你不想用一键脚本，也可以手动执行：

### 1. 生成 train / val / test 切分和 `dataset.yaml`

```bash
python prepare_garbage4_dataset.py \
  --dataset-root /workspace/garbage_train/garbage_dataset \
  --output-dir /workspace/garbage_train/workdir/dataset
```

### 2. 启动训练

```bash
python train_yolo_garbage.py \
  --data /workspace/garbage_train/workdir/dataset/dataset.yaml \
  --model yolov8s.pt \
  --epochs 50 \
  --imgsz 640 \
  --device 0 \
  --batch 16 \
  --workers 8 \
  --project /workspace/garbage_train/workdir/runs \
  --name garbage4_yolov8s
```

## 推荐策略

先跑一版：

```bash
yolov8s.pt + 50 epochs
```

如果效果还不够，再试：

```bash
yolov8m.pt + 80 epochs
```

## 注意

1. 你这个数据集是检测数据集，不是分类数据集，所以训练出来的是“检测模型”。
2. 如果服务器显存只有 8GB 左右，优先把 `batch` 调小到 `8` 或 `4`。
3. 如果数据集类别已经固定为 4 类，网页端就应该优先加载你自己训练的 `best.pt`，不要再让开放词汇模型做主判定。
