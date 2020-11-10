# TechConf Registration Website

## Project Overview
The TechConf website allows attendees to register for an upcoming conference. Administrators can also view the list of attendees and notify all attendees via a personalized email message.

The application is currently working but the following pain points have triggered the need for migration to Azure:
 - The web application is not scalable to handle user load at peak
 - When the admin sends out notifications, it's currently taking a long time because it's looping through all attendees, resulting in some HTTP timeout exceptions
 - The current architecture is not cost-effective 

In this project, you are tasked to do the following:
- Migrate and deploy the pre-existing web app to an Azure App Service
- Migrate a PostgreSQL database backup to an Azure Postgres database instance
- Refactor the notification logic to an Azure Function via a service bus queue message

## Dependencies

You will need to install the following locally:
- [Postgres](https://www.postgresql.org/download/)
- [Visual Studio Code](https://code.visualstudio.com/download)
- [Azure Function tools V3](https://docs.microsoft.com/en-us/azure/azure-functions/functions-run-local?tabs=windows%2Ccsharp%2Cbash#install-the-azure-functions-core-tools)
- [Azure CLI](https://docs.microsoft.com/en-us/cli/azure/install-azure-cli?view=azure-cli-latest)
- [Azure Tools for Visual Studio Code](https://marketplace.visualstudio.com/items?itemName=ms-vscode.vscode-node-azure-pack)

## Project Instructions

### Part 1: Create Azure Resources and Deploy Web App
1. Create a Resource group
2. Create an Azure Postgres Database single server
   - Add a new database `techconfdb`
   - Allow all IPs to connect to database server
   - Restore the database with the backup located in the data folder
3. Create a Service Bus resource with a `notificationqueue` that will be used to communicate between the web and the function
   - Open the web folder and update the following in the `config.py` file
      - `POSTGRES_URL`
      - `POSTGRES_USER`
      - `POSTGRES_PW`
      - `POSTGRES_DB`
      - `SERVICE_BUS_CONNECTION_STRING`
4. Create App Service plan
5. Create a storage account
6. Deploy the web app

```azcli
# Resource Group
az group create -n $RESOURCE_GROUP -l $REGION

# Postgress DB
az postgres server create -n $PGS_NAME -l $REGION -g $RESOURCE_GROUP --sku-name $PGS_SKU -p $PGS_PASSWORD -u $PGS_USER --version 11
az postgres server firewall-rule create --resource-group $RESOURCE_GROUP --server $PGS_NAME --name AllowIP --start-ip-address 0.0.0.0 --end-ip-address 255.255.255.255
az postgres server show --resource-group $RESOURCE_GROUP --name $PGS_NAME
az postgres db create -n $PGDB_NAME -g $RESOURCE_GROUP -s $PGS_NAME
## Restore DB
pg_restore --host course3pgserver.postgres.database.azure.com --port 5432 -U ${PGS_USER}@course3pgserver.postgres.database.azure.com --no-tablespaces -W -O -F t -x -d $PGDB_NAME -1 data/techconfdb_backup.tar

# Service Bus
az servicebus namespace create --resource-group $RESOURCE_GROUP --name $SERVICE_BUS_NAME --location $REGION
az servicebus queue create --resource-group $RESOURCE_GROUP --namespace-name $SERVICE_BUS_NAME --name $SERVICE_BUS_QUEUE
az servicebus namespace authorization-rule keys list --resource-group $RESOURCE_GROUP --namespace-name $SERVICE_BUS_NAME --name RootManageSharedAccessKey --query primaryConnectionString --output tsv    

# Storage account
az storage account create -n $STORAGE_ACCOUNT -g $RESOURCE_GROUP

# Web app
cd web/
az webapp up -g $RESOURCE_GROUP -p $APP_SERVICE_PLAN -n $WEBAPP_NAME --runtime "python|3.6" --os-type Linux -l $REGION --sku F1
cd ..
```

### Part 2: Create and Publish Azure Function
1. Create an Azure Function in the `function` folder that is triggered by the service bus queue created in Part 1.

      **Note**: Skeleton code has been provided in the **README** file located in the `function` folder. You will need to copy/paste this code into the `__init.py__` file in the `function` folder.
      - The Azure Function should do the following:
         - Process the message which is the `notification_id`
         - Query the database using `psycopg2` library for the given notification to retrieve the subject and message
         - Query the database to retrieve a list of attendees (**email** and **first name**)
         - Loop through each attendee and send a personalized subject message
         - After the notification, update the notification status with the total number of attendees notified
2. Publish the Azure Function

```azcli
#Function app
func init function --python
cd function/
func new --name $FAPP_NAME --template "Azure Service Bus Queue trigger"

az functionapp create --resource-group $RESOURCE_GROUP --consumption-plan-location westeurope --runtime python --runtime-version 3.8 --functions-version 3 --name $FAPP_NAME --storage-account $STORAGE_ACCOUNT --os-type Linux

func azure functionapp publish $FAPP_NAME --publish-local-settings
cd ..
```

### Part 3: Refactor `routes.py`
1. Refactor the post logic in `web/app/routes.py -> notification()` using servicebus `queue_client`:
   - The notification method on POST should save the notification object and queue the notification id for the function to pick it up
2. Re-deploy the web app to publish changes

```azcli
cd web/
az webapp up
cd ..
```

## Monthly Cost Analysis
Complete a month cost analysis of each Azure resource to give an estimate total cost using the table below:

| Azure Resource | Service Tier | Monthly Cost |
| ------------ | ------------ | ------------ |
| *Azure Postgres Database* | Basic, Gen5, 1 vCore | $35.32 |
| *Azure Service Bus*   | Basic | $0.05 |
| *App Service* | Free, F1 | $0.00 |
| *Storage account* | General purpose V2, Hot access | $21.84 |
| *Azure Functions* | Consumption | $0.00 |
| **Total cost** | | **$57.21** |

## Architecture Explanation
We have deployed our site using an Azure Web App.
It is easy to setup and we need to focus only on the business logic, since infrastructure is managed by Azure and we are covered by the hardware limitations of this approach.
It is the less expensive option in Azure, however we always pay for the service plan even if the application is not running.
For this project we chose the Free option which offers 60 minutes of compute time on shared infrastructure.
Alternatively, a Basic B1 instance would cost around $13 per month depending on the region.

We have used an Azure Function, an event driven executable, which is suitable for short-time stateless tasks.
In this project, an azure function triggered by our web-app when posting a message to the service bus queue is responsible for sending emails and updating the notification status in the database.
For the hosting option, we have chosen the consumption plan, since we pay only for resources based on execution time. Additionally, the first 1 million executions cost nothing and we don't expect our application to have more executions during its lifespan. Alternatively, a more cost-effective approach would be to use the same service plan as our web app.
