const express = require('express');
const axios = require('axios');
const axiosRetry = require('axios-retry').default;
const app = express();

app.use(express.json());

const DJANGO_SERVICE_URL = 'http://django-backend-service:8000';


// CONCURRENT RETRY LOGIC (EXPONENTIAL BACKOFF WITH JITTER)
axiosRetry(axios, {
    retries: 3,
    retryCondition: (error) => {
        return axiosRetry.isNetworkOrIdempotentRequestError(error) || error.response?.status >= 500;
    },
    retryDelay: (retryCount) => {
        console.log(`Network blip intercepted. Initiating retry attempt #${retryCount}...`);
        return retryCount * 1000; // Exponential delay: 1s, 2s, 3s
    }
});

//  THE CIRCUIT BREAKER STATE MACHINE
class CircuitBreaker {
    constructor(breakerName, failureThreshold = 3, recoveryTimeoutMs = 15000) {
        this.breakerName = breakerName;
        this.failureThreshold = failureThreshold;
        this.recoveryTimeoutMs = recoveryTimeoutMs;
        this.state = 'CLOSED'; // States: CLOSED (Healthy), OPEN (Tripped), HALF-OPEN (Testing)
        this.failureCount = 0;
        this.nextRetryTime = 0;

    }

     async execute(apiCall, fallbackPayload) {
        const currentTime = Date.now();

        if (this.state === 'OPEN') {
            if (currentTime >= this.nextRetryTime) {
                console.log("Circuit Breaker transitioning to HALF-OPEN. Testing upstream stability...");
                this.state = 'HALF-OPEN';
            } else {
                 console.log("[CIRCUIT BREAKER: OPEN] Short-circuiting request. Serving fallback cache data instantly.");
                 return fallbackPayload;
            }
        } 
        try {
            const response = await apiCall();
            
            // If request clears successfully, reset the breaker state machine
            if (this.state === 'HALF-OPEN' || this.state === 'CLOSED') {
                this.state = 'CLOSED';
                this.failureCount = 0;
                console.log("✅ Circuit Breaker status: CLOSED (Upstream system stable).");
            }
            return response.data;
        } catch (error) {
            this.failureCount += 1;
            console.error(`Upstream failure intercepted (${this.failureCount}/${this.failureThreshold}) for ${this.breakerName} with error : ${error.message}`);

            if (this.failureCount >= this.failureThreshold || this.state === 'HALF-OPEN') {
                this.state = 'OPEN';
                this.nextRetryTime = Date.now() + this.recoveryTimeoutMs;
                console.error(`[CIRCUIT BREAKER ${this.breakerName}: TRIPPED] Moving to OPEN state for the next ${this.recoveryTimeoutMs / 1000}s.`);
            }
            return fallbackPayload;
        }
     }
}

const dashboardBreaker  = new CircuitBreaker('Dashboard-Aggregator-Breaker');
const challengeIngestBreaker = new CircuitBreaker('Challenge-Ingestion-Breaker');
const sandboxBreaker    = new CircuitBreaker('Sandbox-Submission-Polling-Breaker');


// Web Routes: 

app.get('/api/dashboard/course-experience/:userId/:courseId', async (req, res) => {
    const { userId, courseId } = req.params;

    const currentSecond = req.query.second ? parseInt(req.query.second) : 0;
    console.log(`Dashboard Aggregator: Fetching data for User: ${userId}, Course: ${courseId}, Second: ${currentSecond}`);
    
    // Define mock fallback data payload if Django completely crashes down the line
    const staticFallbackPayload = {
        userId,
        courseContext: { courseId, estimatedMinutes: 45, level: "Fallback Mock Mode" },
        userTrackingMetrics: { status: "OFFLINE_MODE_CACHE", is_completed: false },
        gatewayMetadata: { circuitBreakerTriggered: true, notice: "Upstream system currently recovering." }
    };


    // Execute network requests inside the protective boundary of the circuit breaker wrapper
    const output = await dashboardBreaker.execute(async () => {
        return await axios.post(`${DJANGO_SERVICE_URL}/api/v1/progress/`, {
            user_id: parseInt(userId), course_id: parseInt(courseId), second: currentSecond
        });
    }, staticFallbackPayload);

    return res.status(200).json(output);
});

// Proxies write requests
app.post('/api/gateway/course-ingest', async (req, res) => {
    console.log("Ingestion Gateway: Proxying inbound course creation payload down to Django...");

    const ingestionFallback = {
        gateway_status: "CIRCUIT_BREAKER_REDIRECT_MODE",
        upstream_response: { status: "failed_to_persist", reason: "Upstream database cluster unreachable. Retrying later." }
    };

    const outputData = await challengeIngestBreaker.execute(async () => {
        return await axios.post(`${DJANGO_SERVICE_URL}/api/v1/challenges/create/`, req.body);
    }, ingestionFallback);

    return res.status(outputData.gateway_status === "CIRCUIT_BREAKER_REDIRECT_MODE" ? 503 : 201).json(outputData);
});


app.post('/api/gateway/challenges/:challengeId/submit', async (req, res) => {
   const { challengeId } = req.params;
    console.log(`Code Sandbox Gateway: Routing solution strings for Evaluation. Challenge ID: ${challengeId}`);

    const submissionFallback = {
        status: "FALLBACK_GATEWAY_DEGRADED_MODE",
        tracking_task_id: null,
        details: "The sandbox execution queue is currently undergoing maintenance. Please resubmit shortly."
    };

    const outputData = await sandboxBreaker.execute(async () => {
        return await axios.post(`${DJANGO_SERVICE_URL}/api/v1/challenges/${challengeId}/submit/`, req.body);
    }, submissionFallback);

    return res.status(outputData.status === "FALLBACK_GATEWAY_DEGRADED_MODE" ? 503 : 202).json(outputData);
});


app.get('/api/gateway/tasks/:taskId', async (req,res) => {
     const { taskId } = req.params;
    console.log(`Polling Gateway: Inspecting compilation result state for Task UUID: ${taskId}`);

    const pollingFallback = {
        task_id: taskId,
        status: "UNKNOWN_CLUSTER_OFFLINE",
        result: { error: "Metrics and tasks tracking databases are temporarily unreachable." }
    };

    const outputData = await sandboxBreaker.execute(async () => {
        return await axios.get(`${DJANGO_SERVICE_URL}/api/v1/challenges/tasks/${taskId}/`);
    }, pollingFallback);

    return res.status(200).json(outputData);
});

const PORT = 3000;
app.listen(PORT, ()=>{
    console.log(`Resilient Edge Gateway operating completely under Circuit Breaker boundaries on internal port ${PORT}`);
});