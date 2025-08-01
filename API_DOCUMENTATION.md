# 🚀 Pinnacle Betting Similarity API Documentation

## Table of Contents
1. [Overview](#overview)
2. [Authentication](#authentication)
3. [Base URL](#base-url)
4. [Request/Response Format](#requestresponse-format)
5. [Endpoints](#endpoints)
6. [Data Models](#data-models)
7. [Code Examples](#code-examples)
8. [Error Handling](#error-handling)
9. [Rate Limiting](#rate-limiting)
10. [Testing](#testing)

## Overview

The Pinnacle Betting Similarity API provides programmatic access to sports betting odds similarity analysis. This RESTful API allows external systems to:

- Analyze similarity between betting odds
- Compare different similarity calculation methods
- Collect and manage betting data
- Monitor system performance
- Access database statistics

**API Version:** 2.0.0  
**Base Technology:** FastAPI with Pydantic validation  
**Response Format:** JSON  
**Documentation:** Auto-generated with OpenAPI/Swagger

## Authentication

Currently, the API does not require authentication. For production deployments, consider implementing:
- API key authentication
- JWT tokens
- Rate limiting by IP/user

## Base URL

```
Production: https://your-domain.com/api
Development: http://localhost:8000/api
```

All API endpoints are prefixed with `/api` to ensure proper routing through Kubernetes ingress.

## Request/Response Format

### Request Headers
```http
Content-Type: application/json
Accept: application/json
```

### Standard Response Format
```json
{
  "success": true,
  "data": {},
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Error Response Format
```json
{
  "success": false,
  "error": "ErrorType",
  "message": "Error description",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Endpoints

### 🏥 Health & Monitoring

#### GET `/api/health`
Check API health status and system metrics.

**Response:**
```json
{
  "status": "healthy",
  "timestamp": "2024-01-01T12:00:00.000Z",
  "version": "2.0.0",
  "uptime": 3600,
  "checks": {
    "database": "ok",
    "memory_usage": 45.2,
    "cpu_usage": 12.5
  }
}
```

#### GET `/api/metrics`
Retrieve detailed system and application metrics.

**Response:**
```json
{
  "system_metrics": {
    "memory_usage": 45.2,
    "cpu_usage": 12.5,
    "disk_usage": 60.0
  },
  "application_metrics": {
    "total_requests": 10543,
    "successful_requests": 10234,
    "error_rate": 2.9
  },
  "recent_metrics": {
    "last_hour": {
      "requests_count": 156,
      "avg_response_time": 0.245
    }
  }
}
```

### 🔍 Similarity Analysis

#### POST `/api/similarity/analyze`
Analyze similarity for given betting odds.

**Request Body:**
```json
{
  "odds": {
    "home": 2.1,
    "draw": 3.4,
    "away": 3.2,
    "over_25": 1.85,
    "under_25": 1.95
  },
  "method": "cosine",
  "threshold": 0.90,
  "min_matches": 10
}
```

**Response:**
```json
{
  "success": true,
  "request_params": {
    "method": "cosine",
    "threshold": 0.90,
    "min_matches": 10
  },
  "similar_matches": [
    {
      "match_id": "123",
      "date": "2024-01-01",
      "teams": "Team A vs Team B",
      "odds": {
        "home": 2.05,
        "draw": 3.3,
        "away": 3.25,
        "over_25": 1.88,
        "under_25": 1.92
      },
      "similarity": 0.94,
      "result": "home_win"
    }
  ],
  "analysis": {
    "total_matches": 25,
    "home_win_percentage": 40.0,
    "draw_percentage": 20.0,
    "away_win_percentage": 40.0,
    "confidence": 85.5
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### GET `/api/similarity/methods`
Get available similarity calculation methods.

**Response:**
```json
{
  "methods": ["cosine", "euclidean", "percentage"],
  "default_method": "cosine",
  "descriptions": {
    "cosine": "Mesure l'angle entre deux vecteurs de cotes",
    "euclidean": "Mesure la distance géométrique entre les cotes",
    "percentage": "Calcule la différence relative moyenne"
  }
}
```

#### POST `/api/similarity/compare-methods`
Compare results using different similarity methods.

**Request Body:**
```json
{
  "home": 2.1,
  "draw": 3.4,
  "away": 3.2,
  "over_25": 1.85,
  "under_25": 1.95
}
```

**Response:**
```json
{
  "success": true,
  "odds": {
    "home": 2.1,
    "draw": 3.4,
    "away": 3.2,
    "over_25": 1.85,
    "under_25": 1.95
  },
  "method_comparison": {
    "cosine": {
      "matches_found": 25,
      "avg_similarity": 0.92,
      "confidence": 85.5
    },
    "euclidean": {
      "matches_found": 18,
      "avg_similarity": 0.89,
      "confidence": 78.2
    },
    "percentage": {
      "matches_found": 22,
      "avg_similarity": 0.91,
      "confidence": 82.1
    }
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### 📊 Database Operations

#### GET `/api/database/stats`
Get database statistics and information.

**Response:**
```json
{
  "success": true,
  "stats": {
    "total_matches": 15420,
    "recent_matches": 245,
    "database_size": "12.5 MB",
    "oldest_match": "2023-01-01",
    "newest_match": "2024-01-01",
    "leagues_count": 15
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### POST `/api/database/optimize`
Optimize database performance (background task).

**Response:**
```json
{
  "success": true,
  "message": "Database optimization started in background",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### 📥 Data Collection

#### POST `/api/data/collect`
Start data collection process.

**Request Body:**
```json
{
  "max_events": 1000,
  "source": "current"
}
```

**Parameters:**
- `max_events`: Maximum number of events to collect (1-10000)
- `source`: Data source - "current" or "historical"

**Response:**
```json
{
  "success": true,
  "message": "Current markets collection started (max 1000 events)",
  "source": "current",
  "max_events": 1000,
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### GET `/api/data/collection-stats`
Get data collection statistics.

**Response:**
```json
{
  "success": true,
  "stats": {
    "last_collection": "2024-01-01T11:30:00.000Z",
    "total_collected": 15420,
    "collection_rate": "95.5%",
    "errors_count": 12,
    "processing_time": 245.5
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### GET `/api/matches/today-france`
Get today's matches available for betting in France (ANJ compliant).

**Response:**
```json
{
  "success": true,
  "matches": [
    {
      "event_id": 50001,
      "league_name": "Ligue 1",
      "home_team": "PSG",
      "away_team": "Lyon",
      "start_time": "2024-01-01T20:00:00",
      "match_date": "2024-01-01",
      "home_odds": 1.75,
      "draw_odds": 3.80,
      "away_odds": 4.20,
      "over_25_odds": 1.85,
      "under_25_odds": 1.95,
      "betting_available_france": true,
      "french_regulation_compliant": true,
      "country_restrictions": "FR_ALLOWED"
    }
  ],
  "count": 12,
  "country": "France",
  "regulation_compliance": "ANJ (Autorité Nationale des Jeux)",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### POST `/api/matches/filter-france`
Filter a list of matches according to French betting regulations.

**Request Body:**
```json
[
  {
    "event_id": 12345,
    "league_name": "Premier League",
    "home_team": "Arsenal",
    "away_team": "Chelsea",
    "home_odds": 2.1,
    "draw_odds": 3.4,
    "away_odds": 3.2
  }
]
```

**Response:**
```json
{
  "success": true,
  "original_count": 25,
  "filtered_count": 18,
  "filtered_matches": [
    {
      "event_id": 12345,
      "league_name": "Premier League",
      "home_team": "Arsenal",
      "away_team": "Chelsea",
      "home_odds": 2.1,
      "draw_odds": 3.4,
      "away_odds": 3.2,
      "betting_available_france": true,
      "french_regulation_compliant": true,
      "authorized_reason": "authorized_league",
      "country_restrictions": "FR_ALLOWED"
    }
  ],
  "filter_ratio": 72.0,
  "country": "France",
  "regulation_compliance": "ANJ compliant",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### 🗑️ Cache Management

#### DELETE `/api/cache/similarity`
Clear similarity calculation cache.

**Response:**
```json
{
  "success": true,
  "message": "Cache cleared successfully. 1247 entries deleted.",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### 📈 Performance & Alerts

#### GET `/api/performance/report`
Generate performance report.

**Query Parameters:**
- `hours`: Number of hours to include in report (1-168, default: 24)

**Example:** `/api/performance/report?hours=48`

**Response:**
```json
{
  "success": true,
  "report": {
    "period": "48 hours",
    "total_requests": 5420,
    "avg_response_time": 0.234,
    "error_rate": 2.1,
    "peak_usage": {
      "time": "2024-01-01T14:30:00.000Z",
      "requests_per_minute": 45
    },
    "slowest_endpoints": [
      {
        "endpoint": "/api/similarity/analyze",
        "avg_time": 0.456
      }
    ]
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### GET `/api/alerts`
Get system alerts.

**Query Parameters:**
- `severity`: Filter by severity - "warning" or "critical" (optional)

**Response:**
```json
{
  "success": true,
  "alerts": [
    {
      "id": "alert_001",
      "severity": "warning",
      "message": "High memory usage detected",
      "timestamp": "2024-01-01T11:45:00.000Z",
      "resolved": false
    }
  ],
  "count": 1,
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

## Data Models

### OddsInput
```json
{
  "home": 2.1,      // Home team win odds (1.01-1000)
  "draw": 3.4,      // Draw odds (1.01-1000)
  "away": 3.2,      // Away team win odds (1.01-1000)
  "over_25": 1.85,  // Over 2.5 goals odds (1.01-1000)
  "under_25": 1.95  // Under 2.5 goals odds (1.01-1000)
}
```

### SimilarityRequest
```json
{
  "odds": {}, // OddsInput object
  "method": "cosine", // "cosine", "euclidean", or "percentage"
  "threshold": 0.90,  // Similarity threshold (0-1)
  "min_matches": 10   // Minimum matches to find (1-100)
}
```

### DataCollectionRequest
```json
{
  "max_events": 1000, // Maximum events (1-10000)
  "source": "current" // "current" or "historical"
}
```

## Code Examples

### Python (requests)
```python
import requests
import json

# Base URL
BASE_URL = "http://localhost:8000/api"

# Analyze similarity
def analyze_similarity():
    url = f"{BASE_URL}/similarity/analyze"
    
    payload = {
        "odds": {
            "home": 2.1,
            "draw": 3.4,
            "away": 3.2,
            "over_25": 1.85,
            "under_25": 1.95
        },
        "method": "cosine",
        "threshold": 0.90,
        "min_matches": 10
    }
    
    response = requests.post(url, json=payload)
    
    if response.status_code == 200:
        data = response.json()
        print(f"Found {len(data['similar_matches'])} similar matches")
        return data
    else:
        print(f"Error: {response.status_code} - {response.text}")
        return None

# Get system health
def check_health():
    url = f"{BASE_URL}/health"
    response = requests.get(url)
    
    if response.status_code == 200:
        health = response.json()
        print(f"API Status: {health['status']}")
        print(f"Uptime: {health['uptime']} seconds")
        return health
    else:
        print(f"Health check failed: {response.status_code}")
        return None

# Usage
if __name__ == "__main__":
    # Check API health
    health = check_health()
    
    # Analyze similarity
    if health and health['status'] == 'healthy':
        results = analyze_similarity()
        if results:
            print(f"Analysis confidence: {results['analysis']['confidence']}%")
```

### JavaScript (fetch)
```javascript
const BASE_URL = 'http://localhost:8000/api';

// Analyze similarity
async function analyzeSimilarity() {
    const url = `${BASE_URL}/similarity/analyze`;
    
    const payload = {
        odds: {
            home: 2.1,
            draw: 3.4,
            away: 3.2,
            over_25: 1.85,
            under_25: 1.95
        },
        method: 'cosine',
        threshold: 0.90,
        min_matches: 10
    };
    
    try {
        const response = await fetch(url, {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
            },
            body: JSON.stringify(payload)
        });
        
        if (response.ok) {
            const data = await response.json();
            console.log(`Found ${data.similar_matches.length} similar matches`);
            return data;
        } else {
            console.error(`Error: ${response.status} - ${await response.text()}`);
            return null;
        }
    } catch (error) {
        console.error('Request failed:', error);
        return null;
    }
}

// Get database stats
async function getDatabaseStats() {
    const url = `${BASE_URL}/database/stats`;
    
    try {
        const response = await fetch(url);
        
        if (response.ok) {
            const data = await response.json();
            console.log(`Database contains ${data.stats.total_matches} matches`);
            return data;
        } else {
            console.error(`Error: ${response.status}`);
            return null;
        }
    } catch (error) {
        console.error('Request failed:', error);
        return null;
    }
}

// Usage
analyzeSimilarity().then(results => {
    if (results) {
        console.log(`Analysis confidence: ${results.analysis.confidence}%`);
    }
});

getDatabaseStats();
```

### cURL Examples
```bash
# Check API health
curl -X GET "http://localhost:8000/api/health"

# Analyze similarity
curl -X POST "http://localhost:8000/api/similarity/analyze" \
  -H "Content-Type: application/json" \
  -d '{
    "odds": {
      "home": 2.1,
      "draw": 3.4,
      "away": 3.2,
      "over_25": 1.85,
      "under_25": 1.95
    },
    "method": "cosine",
    "threshold": 0.90,
    "min_matches": 10
  }'

# Get similarity methods
curl -X GET "http://localhost:8000/api/similarity/methods"

# Start data collection
curl -X POST "http://localhost:8000/api/data/collect" \
  -H "Content-Type: application/json" \
  -d '{
    "max_events": 500,
    "source": "current"
  }'

# Get database statistics
curl -X GET "http://localhost:8000/api/database/stats"

# Clear cache
curl -X DELETE "http://localhost:8000/api/cache/similarity"
```

## Error Handling

### HTTP Status Codes
- `200` - Success
- `400` - Bad Request (validation error)
- `404` - Not Found
- `422` - Unprocessable Entity (Pydantic validation error)
- `500` - Internal Server Error

### Common Error Responses

#### Validation Error (400)
```json
{
  "success": false,
  "error": "Invalid odds input",
  "details": {
    "home": "Odds must be between 1.01 and 1000",
    "threshold": "Threshold must be between 0 and 1"
  },
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

#### Internal Server Error (500)
```json
{
  "success": false,
  "error": "InternalServerError",  
  "message": "An unexpected error occurred",
  "timestamp": "2024-01-01T12:00:00.000Z"
}
```

### Error Handling Best Practices
1. Always check the `success` field in responses
2. Handle HTTP status codes appropriately
3. Log error details for debugging
4. Implement retry logic for transient errors
5. Validate input data before sending requests

## Rate Limiting

Currently, no rate limiting is implemented. For production use, consider:

- **Per-IP limits:** 1000 requests/hour
- **Per-endpoint limits:** 100 requests/minute for analysis endpoints
- **Burst limits:** Allow short bursts up to 50 requests/minute

## Testing

### Interactive Documentation
The API provides interactive documentation at:
- Swagger UI: `http://localhost:8000/api/docs`
- ReDoc: `http://localhost:8000/api/redoc`

### Automated Testing
```python
import unittest
import requests

class TestPinnacleAPI(unittest.TestCase):
    def setUp(self):
        self.base_url = "http://localhost:8000/api"
    
    def test_health_check(self):
        response = requests.get(f"{self.base_url}/health")
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertEqual(data['status'], 'healthy')
    
    def test_similarity_analysis(self):
        payload = {
            "odds": {
                "home": 2.1,
                "draw": 3.4,
                "away": 3.2,
                "over_25": 1.85,
                "under_25": 1.95
            },
            "method": "cosine",
            "threshold": 0.90,
            "min_matches": 10
        }
        
        response = requests.post(f"{self.base_url}/similarity/analyze", json=payload)
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data['success'])
        self.assertIn('similar_matches', data)
        self.assertIn('analysis', data)

if __name__ == '__main__':
    unittest.main()
```

### Performance Testing
```bash
# Install Apache Bench
sudo apt-get install apache2-utils

# Test health endpoint
ab -n 100 -c 10 http://localhost:8000/api/health

# Test similarity analysis (with JSON payload)
ab -n 50 -c 5 -p similarity_payload.json -T application/json http://localhost:8000/api/similarity/analyze
```

## Integration Tips

1. **Caching:** Implement client-side caching for method lists and database stats
2. **Batch Processing:** For multiple analyses, consider implementing a batch endpoint
3. **Webhooks:** Consider implementing webhooks for long-running data collection tasks
4. **Monitoring:** Use the `/api/metrics` endpoint to monitor API usage
5. **Error Recovery:** Implement exponential backoff for failed requests

## Support

For API support and issues:
- Check the `/api/health` endpoint for system status
- Review the `/api/alerts` endpoint for system alerts
- Monitor the `/api/metrics` endpoint for performance issues
- Use interactive documentation for testing endpoints

---

**Last Updated:** January 2024  
**API Version:** 2.0.0  
**Documentation Version:** 1.0.0