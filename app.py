from flask import Flask, render_template, request, jsonify
import json
import random
from datetime import datetime, timedelta
import sqlite3
from contextlib import contextmanager

app = Flask(__name__)

# Database setup
def init_db():
    conn = sqlite3.connect('agriculture.db')
    c = conn.cursor()
    
    # Create tables
    c.execute('''CREATE TABLE IF NOT EXISTS sensor_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  sensor_type TEXT,
                  value REAL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS weather_data
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  temperature REAL,
                  humidity REAL,
                  rainfall REAL,
                  wind_speed REAL,
                  timestamp DATETIME DEFAULT CURRENT_TIMESTAMP)''')
    
    c.execute('''CREATE TABLE IF NOT EXISTS crop_recommendations
                 (id INTEGER PRIMARY KEY AUTOINCREMENT,
                  soil_type TEXT,
                  ph_level REAL,
                  temperature REAL,
                  rainfall REAL,
                  recommended_crop TEXT,
                  confidence REAL)''')
    
    conn.commit()
    conn.close()

@contextmanager
def get_db_connection():
    conn = sqlite3.connect('agriculture.db')
    conn.row_factory = sqlite3.Row
    try:
        yield conn
    finally:
        conn.close()

# Initialize database
init_db()

# Sample data for demonstration
def generate_sample_data():
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Generate sample sensor data
        sensor_types = ['soil_moisture', 'temperature', 'humidity', 'ph_level']
        for _ in range(50):
            sensor_type = random.choice(sensor_types)
            if sensor_type == 'soil_moisture':
                value = round(random.uniform(20, 80), 2)
            elif sensor_type == 'temperature':
                value = round(random.uniform(15, 35), 2)
            elif sensor_type == 'humidity':
                value = round(random.uniform(40, 90), 2)
            else:  # ph_level
                value = round(random.uniform(5.0, 8.5), 2)
            
            timestamp = datetime.now() - timedelta(hours=random.randint(0, 168))
            c.execute('INSERT INTO sensor_data (sensor_type, value, timestamp) VALUES (?, ?, ?)',
                     (sensor_type, value, timestamp))
        
        # Generate sample weather data
        for _ in range(30):
            temp = round(random.uniform(15, 35), 2)
            humidity = round(random.uniform(40, 90), 2)
            rainfall = round(random.uniform(0, 50), 2)
            wind_speed = round(random.uniform(0, 25), 2)
            timestamp = datetime.now() - timedelta(hours=random.randint(0, 168))
            
            c.execute('INSERT INTO weather_data (temperature, humidity, rainfall, wind_speed, timestamp) VALUES (?, ?, ?, ?, ?)',
                     (temp, humidity, rainfall, wind_speed, timestamp))
        
        # Generate sample crop recommendations
        crops_data = [
            ('clay', 6.5, 25, 120, 'Rice', 0.85),
            ('sandy', 7.0, 28, 60, 'Maize', 0.78),
            ('loamy', 6.8, 22, 100, 'Wheat', 0.82),
            ('clay', 7.2, 30, 80, 'Cotton', 0.75),
            ('sandy', 6.0, 20, 150, 'Sugarcane', 0.88)
        ]
        
        for data in crops_data:
            c.execute('INSERT INTO crop_recommendations (soil_type, ph_level, temperature, rainfall, recommended_crop, confidence) VALUES (?, ?, ?, ?, ?, ?)',
                     data)
        
        conn.commit()

# Generate sample data if needed
generate_sample_data()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/dashboard')
def dashboard():
    # Get latest sensor readings
    with get_db_connection() as conn:
        c = conn.cursor()
        
        # Get latest readings for each sensor type
        c.execute('''SELECT sensor_type, value, timestamp 
                     FROM sensor_data 
                     WHERE timestamp = (SELECT MAX(timestamp) FROM sensor_data AS sd 
                                       WHERE sd.sensor_type = sensor_data.sensor_type)''')
        latest_readings = {row['sensor_type']: {'value': row['value'], 'timestamp': row['timestamp']} 
                          for row in c.fetchall()}
        
        # Get weather data
        c.execute('SELECT * FROM weather_data ORDER BY timestamp DESC LIMIT 1')
        weather_data = c.fetchone()
        
        # Get statistics
        c.execute('SELECT AVG(value) as avg_value, sensor_type FROM sensor_data GROUP BY sensor_type')
        sensor_stats = {row['sensor_type']: round(row['avg_value'], 2) for row in c.fetchall()}
    
    return render_template('dashboard.html', 
                         readings=latest_readings,
                         weather=weather_data,
                         stats=sensor_stats)

@app.route('/sensors')
def sensors():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM sensor_data ORDER BY timestamp DESC LIMIT 20')
        sensor_data = c.fetchall()
    
    return render_template('sensors.html', sensor_data=sensor_data)

@app.route('/predictions')
def predictions():
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM crop_recommendations')
        recommendations = c.fetchall()
    
    return render_template('predictions.html', recommendations=recommendations)

@app.route('/analytics')
def analytics():
    return render_template('analytics.html')

# API endpoints
@app.route('/api/sensor_data')
def api_sensor_data():
    sensor_type = request.args.get('type', 'soil_moisture')
    limit = request.args.get('limit', 10)
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT value, timestamp FROM sensor_data WHERE sensor_type = ? ORDER BY timestamp DESC LIMIT ?', 
                 (sensor_type, limit))
        data = [{'value': row['value'], 'timestamp': row['timestamp']} for row in c.fetchall()]
    
    return jsonify(data)

@app.route('/api/weather_data')
def api_weather_data():
    limit = request.args.get('limit', 10)
    
    with get_db_connection() as conn:
        c = conn.cursor()
        c.execute('SELECT * FROM weather_data ORDER BY timestamp DESC LIMIT ?', (limit,))
        data = [dict(row) for row in c.fetchall()]
    
    return jsonify(data)

@app.route('/api/recommend_crop', methods=['POST'])
def recommend_crop():
    data = request.json
    soil_type = data.get('soil_type')
    ph_level = data.get('ph_level')
    temperature = data.get('temperature')
    rainfall = data.get('rainfall')
    
    # Simple AI-based recommendation (in real app, use ML model)
    recommendations = {
        'clay': {'optimal_ph': (6.0, 7.0), 'optimal_temp': (20, 30), 'optimal_rainfall': (100, 200), 'crops': ['Rice', 'Wheat']},
        'sandy': {'optimal_ph': (6.5, 7.5), 'optimal_temp': (25, 35), 'optimal_rainfall': (50, 150), 'crops': ['Maize', 'Groundnut']},
        'loamy': {'optimal_ph': (6.0, 7.5), 'optimal_temp': (15, 30), 'optimal_rainfall': (75, 175), 'crops': ['Wheat', 'Sugarcane', 'Cotton']}
    }
    
    if soil_type in recommendations:
        optimal = recommendations[soil_type]
        score = 0
        
        # Calculate suitability score
        if optimal['optimal_ph'][0] <= ph_level <= optimal['optimal_ph'][1]:
            score += 0.4
        if optimal['optimal_temp'][0] <= temperature <= optimal['optimal_temp'][1]:
            score += 0.3
        if optimal['optimal_rainfall'][0] <= rainfall <= optimal['optimal_rainfall'][1]:
            score += 0.3
        
        return jsonify({
            'recommended_crops': optimal['crops'],
            'confidence_score': round(score, 2),
            'soil_type': soil_type
        })
    
    return jsonify({'error': 'Invalid soil type'}), 400

if __name__ == '__main__':
    app.run(debug=True)