import os
import random
from datetime import datetime
from uuid import uuid4

import pandas as pd
from dateutil.relativedelta import relativedelta

import api
import data_models as dm


def main():
    df = _load_csv_file("cost_analysis_instances.csv")
    datasets = generate_datasets(df)
    datasets_start_trainer_params = generate_datasets_start_trainer_params(df)
    datasets_create_prediction_params = generate_datasets_create_prediction_params(df)

    # This functionality will run one job per dataset
    for dataset, start_trainer_params, create_prediction_params in zip(
        datasets,
        datasets_start_trainer_params,
        datasets_create_prediction_params,
    ):
        tenant_id = f"{os.getenv("TENANT_ID")}-{datetime.now()}"
        api.upload_data_v2(tenant_id, dm.UploadDataPayload([dataset]))
        
        # TODO: Modify this function to accept the start_trainer_params
        api.start_trainer(tenant_id, start_trainer_params)
        
        # TODO: Modify this function to accept the create_prediction_params
        api.create_prediction(tenant_id, create_prediction_params)

    # TODO: Implement functionality that runs multiple datasets in one job
        
    # TODO: Implement parallelization


def generate_datasets(df):
    datasets = []
    for _, row in df.iterrows():
        nbr_months = row["# months"]
        nbr_txns_per_month = row["# txns per month"]
        dataset_id = row["Dataset ID"]
        dataset = _generate_single_dataset(dataset_id, nbr_months, nbr_txns_per_month)
        datasets.append(dataset)
    return datasets


def generate_datasets_start_trainer_params(df):
    datasets_start_trainer_params = []
    for _, row in df.iterrows():
        frequency = row["frequency"]
        horizon = row["horizon"]
        dataset_id = row["Dataset ID"]
        dataset_start_trainer_params = _generate_start_trainer_parameters(
            dataset_id=dataset_id,
            frequency=frequency,
            horizon=horizon,
        )
        datasets_start_trainer_params.append(dataset_start_trainer_params)
    return datasets_start_trainer_params


def generate_datasets_create_prediction_params(df):
    datasets_create_prediction_params = []
    for _, row in df.iterrows():
        dataset_id = row["Dataset ID"]
        dataset_create_prediction_params = _generate_create_prediction_parameters(
            dataset_id=dataset_id,
        )
        datasets_create_prediction_params.append(dataset_create_prediction_params)
    return datasets_create_prediction_params


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

    print(f"Generating dataset {dataset_id}...")
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


def _generate_start_trainer_parameters(
    dataset_id: str,
    frequency: str,
    horizon: int,
) -> dm.StartTrainerParameters:
    return dm.StartTrainerParameterObject(
        **{
            "datasetId": dataset_id,
            "frequency": frequency,
            "horizon": horizon,
        }
    )


def _generate_start_trainer_payload(
    start_trainer_parameters: list[dm.StartTrainerParameters],
) -> dm.StartTrainerPayload:
    return dm.StartTrainerPayload(
        **{
            "parametersArray": [
                start_trainer_parameter_obj
                for start_trainer_parameter_obj in start_trainer_parameters
            ]
        }
    )


def _generate_create_prediction_parameters(
    dataset_id: str,
) -> dm.CreatePredictionParameterObject:
    dm.CreatePredictionParameterObject(
        **{
            "datasetId": dataset_id,
            "currentInventoryLevel": 50.0,
            "wantedServiceLevel": 0.95,
            "replenishmentInterval": dm.ReplenishmentInterval(
                **{
                    "value": 1,
                    "granularity": "M",
                }
            ),
            "supplier": dm.Supplier(
                **{
                    "supplierId": "supplier-1",
                    "leadTime": dm.LeadTime(
                        **{
                            "value": 2,
                            "granularity": "W",
                        }
                    ),
                }
            ),
        }
    )


def _generate_create_prediction_payload(
    create_prediction_parameters: list[dm.CreatePredictionParameterObject],
) -> dm.CreatePredictionPayload:
    return dm.CreatePredictionPayload(
        **{
            "parametersArray": [
                create_prediction_parameter_obj
                for create_prediction_parameter_obj in create_prediction_parameters
            ],
        }
    )


def _load_csv_file(file_name: str) -> pd.DataFrame:
    file_path = f"./{file_name}"
    df = pd.read_csv(file_path)
    return df
