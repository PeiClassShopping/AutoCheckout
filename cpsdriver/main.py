import sys
import logging
from matplotlib import pyplot as plt
import numpy as np

from cpsdriver.clients import (
    CpsMongoClient,
    CpsApiClient,
    TestCaseClient,
)
from cpsdriver.cli import parse_configs
from cpsdriver.log import setup_logger


logger = logging.getLogger(__name__)  # pylint: disable=invalid-name


def main(args=None):
    args = parse_configs(args)
    setup_logger(args.log_level)
    mongo_client = CpsMongoClient(args.db_address)
    api_client = CpsApiClient()
    test_client = TestCaseClient(mongo_client, api_client)
    if 'peiclass2020' not in args.db_address:
        # using the local docker + mongodb
        test_client.load(f"{args.command}-{args.sample}")
    logger.info(f"Available Test Cases are {test_client.available_test_cases}")
    test_client.set_context(args.command, load=False)
    generate_plot(test_client)


def generate_plot(test_client):
    # The collections in the client are "depth", "targets", "plate_data", "frame_message"
    # "depth" contains depth sensor data, not always available
    # "targets" contains the position of people inside the store
    # "plate_data" gives the weight sensor readings
    # "frame_message" contains encoded video data

    data_type = "plate_data"

    # See gondola.png for an illustration of gondola, shelves and plates
    # I am only extracting the data for gondola 5, shelf 2, plate 2
    gondola_id = 5

    extracted_data = {}

    ts = 0.0
    # We get the very first record by fetching the first record after t=0
    print("Loading all weight data... this can take several minutes")
    while True:
        # This is how to fetch from the database one record at a time
        record = test_client.find_first_after_time(data_type, ts)
        # It comes in a list. If the list is empty, there is no more data
        if len(record) == 0: break

        # let's look at a sample of data
        # each record from the database has plate_id, frequency, timestamp, and data
        # The plate_id tells you where in the store this data is located

        # The frequency is the sampling frequency of the data
        # The timestamp is the time the data was collected
        # The data is the raw readings from the sensors
        ts = record[0].timestamp
        # One record has one sample of data for all plates and all shelves in the same gondola
        weight_data = record[0].data
        # The shape of the data is 12 x 7 x 13
        # The first index is time. Each record has 12 samples, and the sampling rate is 60.0Hz, so there is 0.2s of data.
        # The second index is shelves. Shelf 0 is not used and there may be empty shelves at the end
        # The last index is plates. Plate 0 is not used.
        
        gondola_key = record[0].plate_id.gondola_id
        # I am storing the data by gondola
        if gondola_key not in extracted_data:
            extracted_data[gondola_key] = []

        extracted_data[gondola_key].append(weight_data)

    # After we collected all the data, I will plot the weight data for gondola 2, shelf 5, all plates
    # Try to figure out how to plot individual plates to find out which one
    # caused the change
    gondola_2_data = np.concatenate(extracted_data[2], axis=0)
    #print(gondola_2_data.shape)
    shelf5 = np.sum(gondola_2_data[:,5,1:], axis=1)
    #print(d.shape)
    plt.plot(shelf5)
    plt.show()


if __name__ == "__main__":
    main(args=sys.argv[1:])
