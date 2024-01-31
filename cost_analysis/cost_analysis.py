import random
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
from uuid import uuid4

import pandas as pd
from dateutil.relativedelta import relativedelta
from dotenv import find_dotenv, load_dotenv

import api
import data_models as dm

load_dotenv(find_dotenv())

# TODO: Implement data deletion
# TODO: Implement wrap-around for slices
# TODO: Rename slices to something better
# TODO: Refactor this file so it's clean and easy to read
# TODO: Talk to Thea about how to set up this in the sandbox

def main():
    # Prepare the datasets and the parameter settings for the jobs
    df = _load_csv_file("cost_analysis/cost_analysis_instances.csv")
    all_datasets = generate_datasets(df)
    all_st_parameter_objects = generate_st_parameter_objects(df)
    all_cp_parameter_objects = generate_cp_parameter_objects(df)

    # Get the slices of the jobs to run
    slices = get_slices(
        all_datasets,
        all_st_parameter_objects,
        all_cp_parameter_objects,
        datasets_per_slice=5,
    )

    # Run jobs in parallel or sequentially
    run_jobs_in_parallel(slices, break_after=1)
    # run_jobs_sequentially(slices)


def run_jobs_in_parallel(slices, break_after=-1):
    with ThreadPoolExecutor() as executor:
        # Prepare the threads to run
        futures = []
        for i, slice in enumerate(slices):
            future = executor.submit(
                run_upload_train_predict,
                tenant_id=f"io-cost-analysis-test-run-{i}",
                datasets=slice[0],
                st_parameter_objects=slice[1],
                cp_parameter_objects=slice[2],
            )
            futures.append(future)

            # Cut the jobs short if needed
            if i == break_after:
                break

        # Run the threads
        for future in futures:
            future.result()


def run_jobs_sequentially(slices, break_after=-1):
    for i, slice in enumerate(slices):
        run_upload_train_predict(
            tenant_id=f"io-cost-analysis-test-run-{i}",
            datasets=slice[0],
            st_parameter_objects=slice[1],
            cp_parameter_objects=slice[2],
        )

        # Cut the jobs short if needed
        if i == break_after:
            break


def run_upload_train_predict(
    tenant_id: str,  # Name of the run
    datasets: list[dm.Dataset],
    st_parameter_objects: list[dm.StartTrainerParameterObject],
    cp_parameter_objects: list[dm.CreatePredictionParameterObject],
):
    # Upload data
    payload = dm.UploadDataPayload(datasets=datasets)
    api.upload_data_v2(tenant_id, payload)

    # Start trainer
    payload = dm.StartTrainerPayload(parametersArray=st_parameter_objects)
    api.start_trainer_v2(tenant_id, payload)

    # Create prediction
    payload = dm.CreatePredictionPayload(parametersArray=cp_parameter_objects)
    api.create_prediction_v2(tenant_id, payload)


def generate_datasets(df):
    datasets = []
    for _, row in df.iterrows():
        nbr_months = row["# months"]
        nbr_txns_per_month = row["# txns per month"]
        dataset_id = row["Dataset ID"]
        dataset = _generate_single_dataset(dataset_id, nbr_months, nbr_txns_per_month)
        datasets.append(dataset)
    return datasets


def generate_st_parameter_objects(df):
    st_parameter_objects = []
    for _, row in df.iterrows():
        frequency = row["frequency"]
        horizon = row["horizon"]
        dataset_id = row["Dataset ID"]
        st_parameter_object = _get_st_parameter_object(
            dataset_id=dataset_id,
            frequency=frequency,
            horizon=horizon,
        )
        st_parameter_objects.append(st_parameter_object)
    return st_parameter_objects


def _get_st_parameter_object(
    dataset_id: str,
    frequency: str,
    horizon: int,
) -> dm.StartTrainerParameterObject:
    return dm.StartTrainerParameterObject(
        **{
            "datasetId": dataset_id,
            "frequency": frequency,
            "horizon": horizon,
        }
    )


def generate_cp_parameter_objects(df):
    cp_parameter_objects = []
    for _, row in df.iterrows():
        dataset_id = row["Dataset ID"]
        cp_parameter_object = _get_cp_parameter_object(
            dataset_id=dataset_id,
        )
        cp_parameter_objects.append(cp_parameter_object)
    return cp_parameter_objects


def _get_cp_parameter_object(
    dataset_id: str,
) -> dm.CreatePredictionParameterObject:
    return dm.CreatePredictionParameterObject(
        **{
            "datasetId": dataset_id,
            "currentInventoryLevel": 50.0,
            "wantedServiceLevel": 0.95,
            "replenishmentInterval": dm.ReplenishmentInterval(
                **{
                    "value": 1,
                    "granularity": "W",
                }
            ),
            "supplier": dm.Supplier(
                **{
                    "supplierId": "supplier-1",
                    "leadTime": dm.LeadTime(
                        **{
                            "value": 1,
                            "granularity": "W",
                        }
                    ),
                }
            ),
        }
    )


def get_slices(
    datasets,
    start_trainer_params,
    create_prediction_params,
    datasets_per_slice,
):
    # Calculate the number of slices
    num_slices = len(datasets) // datasets_per_slice
    if len(datasets) % datasets_per_slice != 0:
        num_slices += 1

    # Create the slices
    slices = []
    for i in range(num_slices):
        start_index = i * datasets_per_slice
        end_index = start_index + datasets_per_slice
        slices.append(
            (
                datasets[start_index:end_index],
                start_trainer_params[start_index:end_index],
                create_prediction_params[start_index:end_index],
            )
        )

    return slices


def _generate_single_dataset(
    dataset_id: str,
    nbr_months: int,
    nbr_txns_per_month: int,
) -> dm.Dataset:
    """Generate a dataset based on the given parameters.

    The logic starts at the current date, and fills the current month with
    transactions until the current date of the month is reached. Then, it
    moves to the previous month's last date, and fills that month with
    transactions until the last date of the month is reached. This continues
    until the number of months to generate is reached.

    Args:
        dataset_id (str): The ID of the dataset.
        nbr_months (int): The number of months to generate.
        nbr_txns_per_month (int): The number of transactions to generate per month.

    Returns:
        dm.Dataset: The generated dataset.
    """

    # print(f"Generating dataset {dataset_id}...")
    min_quantity = random.uniform(50.0, 300.0)
    max_quantity = random.uniform(min_quantity, min_quantity * 3.0)
    unit_cost = random.uniform(50.0, 150.0)
    unit_price = random.uniform(unit_cost * 1.5, unit_cost * 4.0)
    current_date = datetime.now()
    txns = []

    # Avoid future txns by setting last date of month to current date
    last_date_of_month = current_date
    for _ in range(nbr_months):
        txns_month = []

        # Set the temp date to the first day of the month
        temp_date = last_date_of_month.replace(day=1)
        while temp_date <= last_date_of_month and len(txns_month) < nbr_txns_per_month:
            formatted_date = temp_date.strftime("%Y-%m-%d")
            quantity = random.uniform(min_quantity, max_quantity)
            txn = dm.Transaction(
                quantity=quantity,
                departureDate=formatted_date,
                transactionId=str(uuid4()),
                unitCost=unit_cost,
                unitPrice=unit_price,
            )
            txns_month.append(txn)
            temp_date += relativedelta(days=1)

        # Store the txns of the month
        txns.extend(txns_month)

        # Set the last date of the month to the last day of the previous month
        last_date_of_month = last_date_of_month.replace(day=1) - relativedelta(days=1)

    return dm.Dataset(datasetId=dataset_id, transactions=txns)


def _load_csv_file(file_name: str) -> pd.DataFrame:
    file_path = f"./{file_name}"
    df = pd.read_csv(file_path)
    return df


if __name__ == "__main__":
    main()
