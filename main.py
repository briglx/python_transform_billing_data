#!/usr/bin/python
"""Main script for python boilerplate."""
import argparse
import asyncio
from datetime import datetime
import os

from azure.storage.blob.aio import BlobClient
from dotenv import load_dotenv
import pandas as pd

load_dotenv()
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))

BILLING_DETAIL_TYPES = {
    "InvoiceSectionName": "str",
    "AccountName": "str",
    "AccountOwnerId": "str",
    "SubscriptionId": "str",
    "SubscriptionName": "str",
    "ResourceGroup": "str",
    "ResourceLocation": "str",
    "Date": "str",
    "ProductName": "str",
    "MeterCategory": "str",
    "MeterSubCategory": "str",
    "MeterId": "str",
    "MeterName": "str",
    "MeterRegion": "str",
    "UnitOfMeasure": "str",
    "Quantity": "str",
    "EffectivePrice": "str",
    "CostInBillingCurrency": "float",
    "CostCenter": "str",
    "ConsumedService": "str",
    "ResourceId": "str",
    "Tags": "str",
    "OfferId": "str",
    "AdditionalInfo": "str",
    "ServiceInfo1": "str",
    "ServiceInfo2": "str",
    "ResourceName": "str",
    "ReservationId": "str",
    "ReservationName": "str",
    "UnitPrice": "str",
    "ProductOrderId": "str",
    "ProductOrderName": "str",
    "Term": "str",
    "PublisherType": "str",
    "PublisherName": "str",
    "ChargeType": "str",
    "Frequency": "str",
    "PricingModel": "str",
    "AvailabilityZone": "str",
    "BillingAccountId": "str",
    "BillingAccountName": "str",
    "BillingCurrencyCode": "str",
    "BillingPeriodStartDate": "str",
    "BillingPeriodEndDate": "str",
    "BillingProfileId": "str",
    "BillingProfileName": "str",
    "InvoiceSectionId": "str",
    "IsAzureCreditEligible": "str",
    "PartNumber": "str",
    "PayGPrice": "str",
    "PlanName": "str",
    "ServiceFamily": "str",
    "CostAllocationRuleName": "str",
    # Add more columns as needed
}


async def load_csv_from_azure_blob(blob_url, dest_file):
    """Load csv from azure blob storage."""
    blob_client = BlobClient.from_blob_url(blob_url=blob_url)

    with open(dest_file, "wb") as my_blob:
        stream = await blob_client.download_blob()
        data = await stream.readall()
        my_blob.write(data)

    await blob_client.close()

    print(f"Downloaded blob data to {dest_file}")


async def cost_by_sub(df, dest_dir, file_name):
    """Create cost by sub report."""
    file_path = os.path.join(dest_dir, file_name)
    print(f"Creating Cost by Subscription report to {file_path}")
    agg_df = (
        df.groupby("SubscriptionName")
        .agg({"CostInBillingCurrency": "sum"})
        .reset_index()
    )
    agg_df.to_csv(file_path, index=False)


async def cost_by_meter_cat(df, dest_dir, file_name):
    """Create cost by meter category report."""
    file_path = os.path.join(dest_dir, file_name)
    print(f"Creating Cost by MeterCategory report to {file_path}")
    agg_df = (
        df.groupby("MeterCategory").agg({"CostInBillingCurrency": "sum"}).reset_index()
    )
    agg_df.to_csv(file_path, index=False)


async def cost_by_account(df, dest_dir, file_name):
    """Create Cost by account report."""
    file_path = os.path.join(dest_dir, file_name)
    print(f"Creating Cost by AccountName report to {file_path}")
    agg_df = (
        df.groupby("AccountName").agg({"CostInBillingCurrency": "sum"}).reset_index()
    )
    agg_df.to_csv(file_path, index=False)


async def cost_by_month(df, dest_dir, file_name):
    """Create Cost by month report."""
    file_path = os.path.join(dest_dir, file_name)
    print(f"Creating Cost by Month report to {file_path}")
    agg_df = df.groupby("Month").agg({"CostInBillingCurrency": "sum"}).reset_index()
    agg_df.to_csv(file_path, index=False)


async def main(source, out_dir):
    """Fetch main data."""
    assert len(source) > 0, "Source is required."

    timestamp = datetime.now().strftime("%Y%m%dT%H%M%S")
    report_dir = os.path.join(out_dir, timestamp)
    download_dir = os.path.join(out_dir, "raw")
    billing_file = os.path.join(download_dir, f"{timestamp}.billing.csv")

    # Create temp directories
    os.makedirs(out_dir, exist_ok=True)
    os.makedirs(report_dir, exist_ok=True)
    os.makedirs(download_dir, exist_ok=True)

    # Fetch data
    await load_csv_from_azure_blob(source, billing_file)

    # Load data
    df = pd.read_csv(
        billing_file,
        header=0,
        dtype=BILLING_DETAIL_TYPES,
    )

    # Add temporal columns
    df["Date"] = pd.to_datetime(df["Date"])
    df["Month"] = df["Date"].dt.to_period("M")
    df["Year"] = df["Date"].dt.to_period("Y")

    print(df.head())

    # Create Reports
    await cost_by_sub(df, report_dir, "cost_by_subscription.csv")
    await cost_by_meter_cat(df, report_dir, "cost_by_meter_cat.csv")
    await cost_by_account(df, report_dir, "cost_by_account.csv")
    await cost_by_month(df, report_dir, "cost_by_month.csv")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Python Transform Billing.",
        add_help=True,
    )
    parser.add_argument(
        "--source",
        "-s",
        help="Blob url with SAS token",
    )
    parser.add_argument(
        "--out",
        "-o",
        help="Location to write report.",
    )
    args = parser.parse_args()

    STORAGE_URL = args.source or os.environ.get("STORAGE_URL")
    OUT_FOLDER = args.out or os.environ.get("OUT_FOLDER")

    if not STORAGE_URL:
        raise ValueError(
            "Source is required. Have you set the STORAGE_URL env variable?"
        )

    if not OUT_FOLDER:
        raise ValueError("Out is required. Have you set the OUT_FOLDER env variable?")

    asyncio.run(main(STORAGE_URL, OUT_FOLDER))
