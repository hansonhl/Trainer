#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os
import pathlib
import subprocess
import time
from pprint import pprint

import torch

from trainer import TrainerArgs, logger


def distribute():
    """
    Call 👟Trainer training script in DDP mode.
    """
    parser = TrainerArgs().init_argparse(arg_prefix="")
    parser.add_argument("--script", type=str, help="Target training script to distibute.")
    parser.add_argument(
        "--gpus",
        type=str,
        help='GPU IDs to be used for distributed training in the format ```"0,1"```. Used if ```CUDA_VISIBLE_DEVICES``` is not set.',
    )
    args, unargs = parser.parse_known_args()

    # set active gpus from CUDA_VISIBLE_DEVICES or --gpus
    if "CUDA_VISIBLE_DEVICES" in os.environ:
        num_gpus = torch.cuda.device_count()
        gpus = [str(gpu) for gpu in range(num_gpus)]
    else:
        gpus = args.gpus.split(",")
        num_gpus = len(gpus)

    group_id = time.strftime("%Y_%m_%d-%H%M%S")

    # set arguments for train.py
    folder_path = pathlib.Path(__file__).parent.absolute()
    if os.path.exists(os.path.join(folder_path, args.script)):
        command = [os.path.join(folder_path, args.script)]
    else:
        command = [args.script]

    # Pass all the TrainerArgs fields
    command.append(f"--continue_path={args.continue_path}")
    command.append(f"--restore_path={args.restore_path}")
    command.append(f"--group_id=group_{group_id}")
    command.append("--use_ddp=true")
    command += unargs
    command.append("")

    # run processes
    processes = []
    for rank, local_gpu_id in enumerate(gpus):
        my_env = os.environ.copy()
        my_env["PYTHON_EGG_CACHE"] = f"/tmp/tmp{local_gpu_id}"
        my_env["RANK"] = f"{local_gpu_id}"
        my_env["CUDA_VISIBLE_DEVICES"] = f"{','.join(gpus)}"
        command[-1] = f"--rank={rank}"
        rank_command = ["python3"] + command

        p = subprocess.Popen(rank_command, env=my_env)  # pylint: disable=consider-using-with
        processes.append(p)
        logger.info(rank_command)

    for p in processes:
        p.wait()


if __name__ == "__main__":
    distribute()
