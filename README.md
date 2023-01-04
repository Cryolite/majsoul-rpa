# majsoul-rpa
A Robotic Process Automation (RPA) framework for Mahjong Soul (雀魂)

## Prerequisites

### Protocol Buffers Compiler

Put a [protocol buffers](https://developers.google.com/protocol-buffers) compiler, `protoc`, in a PATH location.

### PyTorch

Install [PyTorch](https://pytorch.org/).

### kanachan

Install [kanachan](https://github.com/Cryolite/kanachan).

```bash
$ pip install git+https://github.com/Cryolite/kanachan
```

### Install Python Dependencies

```bash
majsoul-rpa$ pip install -U .
```

### AWS Credentials

Write AWS credential information in `$HOME/.aws/credentials`'s `majsoul-rpa` profile.

### kanachan's Model

Prepare kanachan's model and write kanachan's model configuration file `model.yaml`.

### Configuration File

Write the configuration file `config.yaml`.
