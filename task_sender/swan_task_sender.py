import csv
import logging
import os
import uuid
import subprocess
from os import listdir
from os.path import isfile, join
from pathlib import Path
from typing import List

from common.OfflineDeal import OfflineDeal
from common.config import read_config
from common.swan_client import SwanClient, SwanTask
from .deal_sender import send_deals
from .service.file_process import checksum, stage_one


def read_file_path_in_dir(dir_path: str) -> List[str]:
    _file_paths = [join(dir_path, f) for f in listdir(dir_path) if isfile(join(dir_path, f))]
    return _file_paths


def generate_csv_and_send(_task: SwanTask, deal_list: List[OfflineDeal], _output_dir: str, _client: SwanClient,
                          _uuid: str):
    _csv_name = _task.task_name + ".csv"
    _csv_path = os.path.join(_output_dir, _csv_name)

    logging.info('Swan task CSV Generated: %s' % _csv_path)
    with open(_csv_path, "w") as csv_file:
        fieldnames = ['uuid', 'miner_id', 'deal_cid', 'payload_cid', 'file_source_url', 'md5', 'start_epoch']
        csv_writer = csv.DictWriter(csv_file, delimiter=',', fieldnames=fieldnames)
        csv_writer.writeheader()
        for _deal in deal_list:
            csv_data = {
                'uuid': _uuid,
                'miner_id': _deal.miner_id,
                'deal_cid': _deal.deal_cid,
                'payload_cid': _deal.data_cid,
                'file_source_url': _deal.car_file_url,
                'md5': _deal.car_file_md5 if _deal.car_file_md5 else "",
                'start_epoch': _deal.start_epoch
            }
            csv_writer.writerow(csv_data)

    if _client:
        with open(_csv_path, "r") as csv_file:
            _client.post_task(_task, csv_file)


def generate_car(_deal_list: List[OfflineDeal], target_dir) -> List[OfflineDeal]:
    csv_path = os.path.join(target_dir, "car.csv")

    with open(csv_path, "w") as csv_file:
        fieldnames = ['car_file_name', 'car_file_path', 'piece_cid', 'data_cid', 'car_file_size', 'car_file_md5',
                      'source_file_name', 'source_file_path', 'source_file_size', 'source_file_md5', 'car_file_url']
        csv_writer = csv.DictWriter(csv_file, delimiter=',', fieldnames=fieldnames)
        csv_writer.writeheader()

        for _deal in _deal_list:
            car_file_name = _deal.source_file_name + ".car"
            car_file_path = os.path.join(target_dir, car_file_name)
            if os.path.isfile(car_file_path):
                # car_file_name = _deal.source_file_name + str(int(time.time())) + ".car"
                car_file_name = _deal.source_file_name + ".car"
                car_file_path = os.path.join(target_dir, car_file_name)

            _deal.car_file_name = car_file_name
            _deal.car_file_path = car_file_path
            car_md5 = ''
            if _deal.car_file_md5:
                car_md5 = checksum(car_file_path)
            #    _deal.car_file_md5 = car_md5

            piece_cid, data_cid = stage_one(_deal.source_file_path, car_file_path)
            # _deal.piece_cid = piece_cid
            # _deal.data_cid = data_cid
            # _deal.car_file_size = os.path.getsize(car_file_path)

            csv_data = {
                'car_file_name': car_file_name,
                'car_file_path': car_file_path,
                'piece_cid': piece_cid,
                'data_cid': data_cid,
                'car_file_size': os.path.getsize(car_file_path),
                'car_file_md5': car_md5,
                'source_file_name': _deal.source_file_name,
                'source_file_path': _deal.source_file_path,
                'source_file_size': _deal.source_file_size,
                'source_file_md5': _deal.source_file_md5,
                'car_file_url': ''
            }
            csv_writer.writerow(csv_data)

    logging.info("Car files output dir: " + target_dir)
    logging.info("Please upload car files to web server or ipfs server.")
    return _deal_list

def go_generate_car(_deal_list: List[OfflineDeal], target_dir) -> List[OfflineDeal]:
    csv_path = os.path.join(target_dir, "car.csv")

    with open(csv_path, "w") as csv_file:
        fieldnames = ['car_file_name', 'car_file_path', 'piece_cid', 'data_cid', 'car_file_size', 'car_file_md5',
                      'source_file_name', 'source_file_path', 'source_file_size', 'source_file_md5', 'car_file_url']
        csv_writer = csv.DictWriter(csv_file, delimiter=',', fieldnames=fieldnames)
        csv_writer.writeheader()

        for _deal in _deal_list:
            car_file_name = _deal.source_file_name + ".car"
            car_file_path = os.path.join(target_dir, car_file_name)
            
            if os.path.isfile(car_file_path):
                # car_file_name = _deal.source_file_name + str(int(time.time())) + ".car"
                car_file_name = _deal.source_file_name + ".car"
                car_file_path = os.path.join(target_dir, car_file_name)
                    
            _deal.car_file_name = car_file_name
            _deal.car_file_path = car_file_path
            car_md5 = ''
            if _deal.car_file_md5:
                car_md5 = checksum(car_file_path)
            #    _deal.car_file_md5 = car_md5

            ###piece_cid, data_cid = stage_one(_deal.source_file_path, car_file_path)
            command_line = "./graphsplit chunk --car-dir={} --slice-size=1000000000 --parallel=2 --graph-name={} --calc-commp=true --parent-path=. {}".format(target_dir, _deal.source_file_name,  _deal.source_file_path)
            subprocess.run((command_line), shell=True)
            
            with open(os.path.join(target_dir,"manifest.csv"),newline='') as csvfile:
                   reader = csv.DictReader(csvfile)
                   for row in reader:
                        if row["filename"] == car_file_name  : 
                            datacid = row["playload_cid"] 
                            car_file_path = os.path.join(target_dir, row["playload_cid"] +'.car')
                            piececid = row["piece_cid"]
                            car_file_name = row["playload_cid"] +'.car'
                            break
             
            # no piece_cid generated. use data_cid instead
            data_cid=datacid
            piece_cid = piececid
            # _deal.piece_cid = piece_cid
            # _deal.data_cid = data_cid
            # _deal.car_file_size = os.path.getsize(car_file_path)
           
            csv_data = {
                'car_file_name': car_file_name,
                'car_file_path': car_file_path,
                'piece_cid': piece_cid,
                'data_cid': data_cid,
                'car_file_size': os.path.getsize(car_file_path),
                'car_file_md5': car_md5,
                'source_file_name': _deal.source_file_name,
                'source_file_path': _deal.source_file_path,
                'source_file_size': _deal.source_file_size,
                'source_file_md5': _deal.source_file_md5,
                'car_file_url': ''
            }
            csv_writer.writerow(csv_data)

    logging.info("Car files output dir: " + target_dir)
    logging.info("Please upload car files to web server or ipfs server.")
    return _deal_list


def generate_metadata_csv(_deal_list: List[OfflineDeal], _task: SwanTask, _out_dir: str, _uuid: str):
    for deal in _deal_list:
        deal.uuid = _uuid
    attributes = [i for i in OfflineDeal.__dict__.keys() if not i.startswith("__")]
    _csv_path = os.path.join(_out_dir, "%s-metadata.csv" % _task.task_name)

    logging.info('Metadata CSV Generated: %s' % _csv_path)
    with open(_csv_path, "w") as csv_file:
        fieldnames = attributes
        csv_writer = csv.DictWriter(csv_file, delimiter=',', fieldnames=fieldnames)
        csv_writer.writeheader()
        for _deal in _deal_list:
            csv_writer.writerow(_deal.__dict__)


def update_task_by_uuid(config_path, task_uuid, miner_fid, csv):
    config = read_config(config_path)
    api_url = config['main']['api_url']
    api_key = config['main']['api_key']
    access_token = config['main']['access_token']
    client = SwanClient(api_url, api_key, access_token)
    client.update_task_by_uuid(task_uuid, miner_fid, csv)


def generate_car_files(input_dir, config_path, out_dir):
    config = read_config(config_path)
    generate_md5 = config['sender']['generate_md5']
    file_paths = read_file_path_in_dir(input_dir)
    output_dir = out_dir
    if not output_dir:
        output_dir = config['sender']['output_dir'] + '/' + str(uuid.uuid4())

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    deal_list: List[OfflineDeal] = []

    for file_path in file_paths:
        source_file_name = os.path.basename(file_path)

        offline_deal = OfflineDeal()
        offline_deal.source_file_name = source_file_name
        offline_deal.source_file_path = file_path
        offline_deal.source_file_size = os.path.getsize(file_path)
        
        if generate_md5:
            offline_deal.car_file_md5 = True
        deal_list.append(offline_deal)

    generate_car(deal_list, output_dir)

def go_generate_car_files(input_dir, config_path, out_dir):
    config = read_config(config_path)
    generate_md5 = config['sender']['generate_md5']
    file_paths = read_file_path_in_dir(input_dir)
    output_dir = out_dir
    if not output_dir:
        output_dir = config['sender']['output_dir'] + '/' + str(uuid.uuid4())

    Path(output_dir).mkdir(parents=True, exist_ok=True)

    deal_list: List[OfflineDeal] = []

    for file_path in file_paths:
        source_file_name = os.path.basename(file_path)

        offline_deal = OfflineDeal()
        offline_deal.source_file_name = source_file_name
        offline_deal.source_file_path = file_path
        offline_deal.source_file_size = os.path.getsize(file_path)
        
        if generate_md5:
            offline_deal.car_file_md5 = True
        deal_list.append(offline_deal)

    go_generate_car(deal_list, output_dir)

def upload_car_files(input_dir, config_path):

    class CarFile:
        car_file_name = None
        car_file_path = None
        piece_cid = None
        data_cid = None
        car_file_size = None
        car_file_md5 = None
        source_file_name = None
        source_file_path = None
        source_file_size = None
        source_file_md5 = None
        car_file_address = None

    attributes = [i for i in CarFile.__dict__.keys() if not i.startswith("__")]

    config = read_config(config_path)
    storage_server_type = config['main']['storage_server_type']
    if storage_server_type == "web server":
        logging.info("Please upload car files to web server manually.")
    else:
        gateway_address = config['ipfs-server']['gateway_address']
        gateway_ip, gateway_port = SwanClient.parseMultiAddr(gateway_address)
        car_files_list: List[CarFile] = []
        car_csv_path = input_dir + "/car.csv"
        with open(car_csv_path, "r") as csv_file:
            reader = csv.DictReader(csv_file, delimiter=',', fieldnames=attributes)
            next(reader, None)
            for row in reader:
                car_file = CarFile()
                for attr in row.keys():
                    car_file.__setattr__(attr, row.get(attr))
                car_files_list.append(car_file)
        for car_file in car_files_list:
            logging.info("Uploading car file %s" % car_file.car_file_name)
            car_file_hash = SwanClient.upload_car_to_ipfs(car_file.car_file_path)
            car_file.car_file_address = "http://" + gateway_ip + ":" + gateway_port + "/ipfs/" + car_file_hash
            logging.info("Car file %s uploaded: %s" % (car_file.car_file_name ,car_file.car_file_address))

        with open(car_csv_path, "w") as csv_file:
            csv_writer = csv.DictWriter(csv_file, delimiter=',', fieldnames=attributes)
            csv_writer.writeheader()
            for car_file in car_files_list:
                csv_writer.writerow(car_file.__dict__)


def create_new_task(input_dir, out_dir, config_path, task_name, curated_dataset, description, miner_id=None):
    # todo move config reading to cli level
    config = read_config(config_path)
    output_dir = out_dir
    if not output_dir:
        output_dir = config['sender']['output_dir']
    public_deal = config['sender']['public_deal']
    verified_deal = config['sender']['verified_deal']
    generate_md5 = config['sender']['generate_md5']
    offline_mode = config['sender']['offline_mode']

    api_url = config['main']['api_url']
    api_key = config['main']['api_key']
    access_token = config['main']['access_token']

    storage_server_type = config['main']['storage_server_type']

    host = config['web-server']['host']
    port = config['web-server']['port']
    path = config['web-server']['path']

    download_url_prefix = str(host).rstrip("/")
    download_url_prefix = download_url_prefix + ":" + str(port)

    task_uuid = str(uuid.uuid4())
    final_csv_path = ""

    path = str(path).strip("/")
    logging.info(
        "Swan Client Settings: Public Task: %s,  Verified Deals: %s,  Connected to Swan: %s, CSV/car File output dir: %s"
        % (str(public_deal).lower(), str(verified_deal).lower(), str(not offline_mode).lower(), output_dir))
    if path:
        download_url_prefix = os.path.join(download_url_prefix, path)
    # TODO: Need to support 2 stage
    if not public_deal:
        if not miner_id:
            print('Please provide --miner for non public deal.')
            exit(1)

    file_paths = read_file_path_in_dir(input_dir)
    Path(output_dir).mkdir(parents=True, exist_ok=True)

    deal_list: List[OfflineDeal] = []

    for file_path in file_paths:
        source_file_name = os.path.basename(file_path)

        offline_deal = OfflineDeal()
        offline_deal.source_file_name = source_file_name
        offline_deal.source_file_path = file_path
        offline_deal.source_file_size = os.path.getsize(file_path)
        if generate_md5:
            offline_deal.car_file_md5 = True
        deal_list.append(offline_deal)

    deal_list: List[OfflineDeal] = []
    csv_file_path = input_dir + "/car.csv"
    with open(csv_file_path, "r") as csv_file:
        fieldnames = ['car_file_name', 'car_file_path', 'piece_cid', 'data_cid', 'car_file_size', 'car_file_md5',
                      'source_file_name', 'source_file_path', 'source_file_size', 'source_file_md5', 'car_file_url']
        reader = csv.DictReader(csv_file, delimiter=',', fieldnames=fieldnames)
        next(reader, None)
        for row in reader:
            deal = OfflineDeal()
            for attr in row.keys():
                deal.__setattr__(attr, row.get(attr))
            deal_list.append(deal)

    # generate_car(deal_list, output_dir)

    if storage_server_type == "web server":
        for deal in deal_list:
            deal.car_file_url = os.path.join(download_url_prefix, deal.car_file_name)

    if not public_deal:
        final_csv_path = send_deals(config_path, miner_id, task_name, deal_list=deal_list, task_uuid=task_uuid, out_dir=output_dir)

    if offline_mode:
        client = None
        logging.info("Working in Offline Mode. You need to manually send out task on filwan.com. ")
    else:
        client = SwanClient(api_url, api_key, access_token)
        logging.info("Working in Online Mode. A swan task will be created on the filwan.com after process done. ")

    task = SwanTask(
        task_name=task_name,
        curated_dataset=curated_dataset,
        description=description,
        is_public=public_deal,
        is_verified=verified_deal
    )

    if miner_id:
        task.miner_id = miner_id

    generate_metadata_csv(deal_list, task, output_dir, task_uuid)
    generate_csv_and_send(task, deal_list, output_dir, client, task_uuid)
