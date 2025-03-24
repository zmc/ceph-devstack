import asyncio
import logging
import sys
from pathlib import Path
from pydoc import ttypager
import os
from datetime import datetime

from ceph_devstack import config, logger, parse_args, VERBOSE
from ceph_devstack.requirements import check_requirements
from ceph_devstack.resources.ceph import CephDevStack


def main():
    args = parse_args(sys.argv[1:])
    config.load(args.config_file)
    if args.verbose:
        for handler in logging.getLogger("root").handlers:
            if not isinstance(handler, logging.FileHandler):
                handler.setLevel(VERBOSE)
    if args.command == "config":
        if args.config_op == "dump":
            print(config.dump())
        if args.config_op == "get":
            print(config.get_value(args.name))
        elif args.config_op == "set":
            config.set_value(args.name, args.value)
        return
    config["args"] = vars(args)
    data_path = Path(config["data_dir"]).expanduser()
    data_path.mkdir(parents=True, exist_ok=True)
    obj = CephDevStack()

    async def run():
        if not await asyncio.gather(
            check_requirements(),
            obj.check_requirements(),
        ):
            logger.error("Requirements not met!")
            sys.exit(1)
        if args.command == "doctor":
            return
        elif args.command == "wait":
            return await obj.wait(container_name=args.container)
        elif args.command == "logs":
            ret=teuthology_logs(str(data_path))
            return ret
        else:
            await obj.apply(args.command)
            return 0

    try:
        sys.exit(asyncio.run(run()))
    except KeyboardInterrupt:
        logger.debug("Exiting!")

def teuthology_logs(data_path:str) -> int:
    """
    This function is used to get the teuthology logs of the latest job run.
    
    Args:
    data_path (str): Path to the data directory.
    """
    list_runs = [f.path for f in os.scandir(data_path + "/archive") if f.is_dir()]
    if len(list_runs) == 0:
        logger.error("No runs found!")
        return 1  
    list_runs.sort(key=lambda x: datetime.strptime(x.split('/')[-1].split('root-')[1].split('-teuthology')[0], '%Y-%m-%d_%H:%M:%S'))
    latest_run = list_runs[-1]
    latest_run_subdir = [f.path for f in os.scandir(latest_run) if f.is_dir()]
    if len(latest_run_subdir) == 0:
        logger.error("No jobs found!")
        return 1
    if len(latest_run_subdir) == 1:
        try:
            if config["args"].get("log_file", False):
                print(f"Log file path: {latest_run_subdir[0]}/teuthology.log")
                return 0
            with open(latest_run_subdir[0] + "/teuthology.log", 'r') as f:
                ttypager(f.read())
            return 0
        except :
            logger.error("No logs found!")
            return 1
    print("Jobs present in latest run:")
    job_ids=[]
    for job in latest_run_subdir:
        job_ids.append(job.split('/')[-1])
        print(f"Job id: {job.split('/')[-1]}")
    job_id=input("Enter any of the above job id to get logs: ")
    if job_id not in job_ids:
        logger.error("Invalid job id!")
        return 1
    try:
        if config["args"].get("log_file", False):
            print(f"Log file path: {latest_run +'/'+ job_id +'/teuthology.log'}")
            return 0    
        with open(latest_run +"/"+ job_id +"/teuthology.log", 'r') as f:
            ttypager(f.read())
    except :
        logger.error("Error reading the logs!")
        return 1
    return 0