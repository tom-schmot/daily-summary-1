from flask import Flask, request, abort
import os
import requests
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from openai import OpenAI

app = Flask(__name__)

# Retrieve credentials from environment variables
tomorrow_api_key = os.getenv('tomorrow_api_key')
news_api_key = os.getenv('news_api_key')
openai_api_key = os.getenv('openai_api_key')
sender_email = os.getenv('sender_email')
sender_password = os.getenv('sender_password')
recipient_email = os.getenv('recipient_email')
SECRET_TOKEN = os.getenv('run_token')

def get_weather(api_key, latitude, longitude):
    try:
        url = f'https://api.tomorrow.io/v4/timelines?location={latitude},{longitude}&fields=temperatureMax,temperatureMin,precipitationProbability,windSpeed,humidity&timesteps=1d&units=imperial&apikey={api_key}'
        response = requests.get(url)
        print(f"URL: {url}")
        print(f"Status Code: {response.status_code}")
        print(f"Response: {response.text}")
        response.raise_for_status()

        data = response.json()
        forecast = data['data']['timelines'][0]['intervals']
        weather_summary = "5-Day Weather Forecast:\n"
        for day in forecast:
            date = day['startTime'].split('T')[0]
            temp_max = day['values']['temperatureMax']
            temp_min = day['values']['temperatureMin']
            precip_prob = day['values']['precipitationProbability']
            wind_speed = day['values']['windSpeed']
            humidity = day['values']['humidity']
            weather_summary += f"{date}: Max Temp: {temp_max}°F, Min Temp: {temp_min}°F, Precipitation Probability: {precip_prob}%, Wind Speed: {wind_speed} mph, Humidity: {humidity}%\n"
        return weather_summary
    except requests.exceptions.RequestException as e:
        return f"Error fetching weather data: {e}"

def get_news(api_key, keywords):
    try:
        news_data = []
        for keyword in keywords:
            url = f'https://newsdata.io/api/1/news?apikey={api_key}&q={keyword}&language=en'
            response = requests.get(url)
            response.raise_for_status()
            data = response.json()
            articles = data.get('results', [])

            keyword_articles = []
            for article in articles:
                content = article.get('content')
                if content == "ONLY AVAILABLE IN PAID PLANS":
                    content = article.get('description') or 'No content available.

                )
                keyword_articles.append({
                    'headline': article.get('title'),
                    'content': content,
                    'source': article.get('link')
                })
        
            news_data.append({
                'keyword': keyword,
                'articles': keyword_articles
            })

        return news_data
    except requests.exceptions.RequestException as e:
        return f"Error fetching news data: {e}"

def summarize_news(api_key, news_data):
    client = OpenAI(api_key=api_key)

    prompt = "Summarize the following news headlines and content by topic. Provide a detailed analysis of major talking points and information you deem important:\n\n"
    for topic in news_data:
        prompt += f"Topic: {topic['keyword']}\n"
        for article in topic['articles']:
            headline = article.get('headline', 'No headline')
            content = article.get('content', 'No content available.')
            prompt += f"- {headline}: {content}\n"
        prompt += "\n"

    response = client.chat.completions.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": "You are a helpful assistant that provides detailed summaries of the news."},
            {"role": "user", "content": prompt}
        ]
    )

    return response.choices[0].message.content

def send_email(sender_email, sender_password, recipient_email, subject, body):
    try:
        msg = MIMEMultipart()
        msg['From'] = sender_email
        msg['To'] = recipient_email
        msg['Subject'] = subject
        msg.attach(MIMEText(body, 'plain'))

        server = smtplib.SMTP_SSL('smtp.gmail.com', 465)
        server.login(sender_email, sender_password)
        server.send_message(msg)
        server.quit()
    except smtplib.SMTPException as e:
        print(f"Error sending email: {e}")

@app.route('/')
def home():
    return "✅ Flask app is running. Use /run-script?token=YOUR_RUN_TOKEN to trigger the script."

@app.route('/run-script', methods=['GET'])
def run_script():
    token = request.args.get('token')
    if token != SECRET_TOKEN:
        abort(403)

    latitude = "41.3341205"
    longitude = "74.2213276"
    keywords = ['Tariffs', 'Artificial Intelligence']

    weather_summary = get_weather(tomorrow_api_key, latitude, longitude)
    
    news_summary = get_news(news_api_key, keywords)
    if isinstance(news_summary, str):
        summarized_news = news_summary  # It's an error message
    else:
        summarized_news = summarize_news(openai_api_key, news_summary)
    
    email_subject = "Daily Update"
    email_body = f"Weather Update:\n{weather_summary}\n\nNews Update:\n{summarized_news}"
    send_email(sender_email, sender_password, recipient_email, email_subject, email_body)

    return "✅ Script executed successfully. Email sent."

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)

