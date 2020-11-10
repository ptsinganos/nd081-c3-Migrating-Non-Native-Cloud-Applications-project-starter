
import logging
import azure.functions as func
import psycopg2
import os
from datetime import datetime
from sendgrid import SendGridAPIClient
from sendgrid.helpers.mail import Mail

def main(msg: func.ServiceBusMessage):

    notification_id = int(msg.get_body().decode('utf-8'))
    logging.info('Python ServiceBus queue trigger processed message: %s',notification_id)

    # TODO: Get connection to database
    conn_string = f"host={os.environ.get('DB_HOST')} dbname={os.environ.get('DB_NAME')} user={os.environ.get('DB_USER')} password={os.environ.get('DB_PASS')}"
    conn = psycopg2.connect(conn_string)
    cursor = conn.cursor()

    try:
        # TODO: Get notification message and subject from database using the notification_id
        cursor.execute(f"SELECT message, subject FROM public.notification WHERE id={notification_id}")
        notification_msg, notification_sub = cursor.fetchone()
        
        # TODO: Get attendees email and name
        cursor.execute(f"SELECT email, concat_ws(' ', first_name, last_name) as name FROM public.attendee")
        attendees = cursor.fetchall()

        # TODO: Loop through each attendee and send an email with a personalized subject
        for (attendee_email, attendee_name) in attendees:
            subject = '{}: {}'.format(attendee_name, notification_sub)
            send_email(attendee_email, subject, notification_msg)
        # TODO: Update the notification table by setting the completed date and updating the status with the total number of attendees notified
        completed_date = datetime.utcnow()
        status = 'Notified {} attendees'.format(len(attendees))
        cursor.execute(
            "UPDATE public.notification SET completed_date=%s, status=%s WHERE id=%s",
            (completed_date, status, notification_id)
        )
        conn.commit()
    except (Exception, psycopg2.DatabaseError) as error:
        logging.error(error)
        conn.rollback()
    finally:
        # TODO: Close connection
        cursor.close()
        conn.close()

def send_email(email, subject, body):
    logging.info(f'Sending email: {email}, {subject}, {body}')
    if not os.environ.get('SENDGRID_API_KEY'):
        logging.warning('Cannot send email. Missing API_KEY')
    else:
        message = Mail(
            from_email=os.environ.get('ADMIN_EMAIL_ADDRESS'),
            to_emails=email,
            subject=subject,
            plain_text_content=body)

        sg = SendGridAPIClient(os.environ.get('SENDGRID_API_KEY'))
        sg.send(message)
