#!/bin/bash

# ================================
# Script: Create and Monitor Change Request in ServiceNow
# Purpose: Automates creation and monitoring of a change request via REST API
# Author: Eshwar Basha Bathini
# ================================

# ========== VARIABLES ==========
SN_INSTANCE="dev214721.service-now.com"
SN_USER="jenkins_api_user"
SN_PASS="5kgiS)[TUmkfVvCiIdxs*]]?g&+SNM[#3CnZyB^tPp5!;J?Fec,I}^!B%5=lIwdEL+TY_+=Er^5niHVHeYz.r_f^?bJe0=2c@kIY"
LOG_FILE="./change_request.log"

ASSIGNMENT_GROUP="Incident Management"
ASSIGNED_TO="jenkins_api_user"

PRIORITY="3"
RISK="2"
IMPACT="2"

CI_SYS_IDS=("281a4d5fc0a8000b00e4ba489a83eedc")
SERVICE_OFFERING_SYS_ID="eshwar"

IMPLEMENTATION_PLAN="Deploy updated Splunk logging integration via Harness CI pipeline."
JUSTIFICATION="Enhances observability and improves log accuracy for production monitoring."
RISK_ANALYSIS="Low risk as changes are limited to log format and routing. Impact is isolated to Splunk integration."
BACKOUT_PLAN="Rollback to previous build artifact and disable new HEC configurations."
TEST_PLAN="Test build in staging; validate log delivery to Splunk and ensure alerts are received."

WAITED_FOR_START=false

echo "=====================================" | tee "$LOG_FILE"
echo "🚀 Creating Change Request..." | tee -a "$LOG_FILE"

# ========== CREATE CHANGE REQUEST ==========
CREATE_RESPONSE=$(curl --silent --show-error -X POST \
  "https://$SN_INSTANCE/api/now/table/change_request" \
  -u "$SN_USER:$SN_PASS" \
  -H "Content-Type: application/json" \
  -d "{
        \"short_description\": \"Automated Change Request from Harness CI Pipeline main\",
        \"description\": \"Triggered automatically via Harness CI/CD pipeline to deploy updated log routing configurations. This change enhances the integration between application logs and Splunk, improves log granularity, and ensures real-time visibility into deployment events. Affects only the logging layer with no changes to core application functionality. Verified in staging prior to production rollout.\",
        \"category\": \"Software\",
        \"priority\": \"$PRIORITY\",
        \"risk\": \"$RISK\",
        \"impact\": \"$IMPACT\",
        \"state\": \"Assess\",
        \"assignment_group\": \"$ASSIGNMENT_GROUP\",
        \"assigned_to\": \"$ASSIGNED_TO\",
        \"implementation_plan\": \"$IMPLEMENTATION_PLAN\",
        \"justification\": \"$JUSTIFICATION\",
        \"u_risk_impact_analysis\": \"$RISK_ANALYSIS\",
        \"backout_plan\": \"$BACKOUT_PLAN\",
        \"test_plan\": \"$TEST_PLAN\",
        \"business_service\": \"IT Services\",
        \"service_offering\": \"$SERVICE_OFFERING_SYS_ID\",
        \"cmdb_ci\": \"${CI_SYS_IDS[0]}\"
      }")

echo "Response: $CREATE_RESPONSE" | tee -a "$LOG_FILE"

# ========== PARSE CHANGE NUMBER ==========
CHANGE_NUMBER=$(echo "$CREATE_RESPONSE" | grep -o '"number":"[^"]*' | sed 's/"number":"//')
if [ -z "$CHANGE_NUMBER" ]; then
  echo "❌ Failed to extract Change Request number" | tee -a "$LOG_FILE"
  exit 1
fi
echo "✅ Created Change Request Number: $CHANGE_NUMBER" | tee -a "$LOG_FILE"

# ========== FETCH SYS_ID ==========
GET_RESPONSE=$(curl --silent --user "$SN_USER:$SN_PASS" \
  "https://$SN_INSTANCE/api/now/table/change_request?sysparm_query=number=$CHANGE_NUMBER")
SYS_ID=$(echo "$GET_RESPONSE" | grep -o '"sys_id":"[^"]*' | sed 's/"sys_id":"//')
if [ -z "$SYS_ID" ]; then
  echo "❌ No such Change Request found with number: $CHANGE_NUMBER" | tee -a "$LOG_FILE"
  exit 1
fi

# ========== LINK AFFECTED CIs ==========
echo "🔗 Linking Affected Configuration Items..." | tee -a "$LOG_FILE"
for CI_SYS_ID in "${CI_SYS_IDS[@]}"; do
  curl --silent --user "$SN_USER:$SN_PASS" -X POST \
    "https://$SN_INSTANCE/api/now/table/task_ci" \
    -H "Content-Type: application/json" \
    -d "{
          \"task\": \"$SYS_ID\",
          \"ci_item\": \"$CI_SYS_ID\"
        }" > /dev/null
  echo "🔧 Linked CI $CI_SYS_ID to Change Request $SYS_ID" | tee -a "$LOG_FILE"
done

# ========== MONITOR CHANGE REQUEST STATE ==========
MAX_RETRIES=1000
SLEEP_INTERVAL=15
COUNT=0
LAST_STATE=""

while [ $COUNT -lt $MAX_RETRIES ]; do
  POLL_RESPONSE=$(curl --silent --user "$SN_USER:$SN_PASS" \
    "https://$SN_INSTANCE/api/now/table/change_request/$SYS_ID")
  CHANGE_STATE=$(echo "$POLL_RESPONSE" | grep -o '"state":"[^"]*' | sed 's/"state":"//')

  if [[ "$CHANGE_STATE" != "$LAST_STATE" ]]; then
    echo "[$(TZ='Asia/Kolkata' date)] 🔄 Change Request State: $CHANGE_STATE" | tee -a "$LOG_FILE"
    LAST_STATE=$CHANGE_STATE
  fi

  if [[ "$CHANGE_STATE" == "-5" ]]; then
    REJECT_REASON=$(echo "$POLL_RESPONSE" | grep -o '"close_notes":"[^"]*' | sed 's/"close_notes":"//' | sed 's/\\n/ /g' | sed 's/\\"/"/g')
    echo "❌ Change Request was rejected." | tee -a "$LOG_FILE"
    echo "📝 Rejection Reason: $REJECT_REASON" | tee -a "$LOG_FILE"
    exit 2
  fi

  if [[ "$CHANGE_STATE" == "-2" && "$WAITED_FOR_START" == "false" ]]; then
    CURRENT_START=$(echo "$POLL_RESPONSE" | grep -o '"start_date":"[^"]*' | sed 's/"start_date":"//' | cut -d'"' -f1)

    if [ -z "$CURRENT_START" ] || [ "$CURRENT_START" == "null" ]; then
      SCHEDULED_START=$(TZ="Asia/Kolkata" date -d '+5 minutes' +"%Y-%m-%d %H:%M:%S")
      SCHEDULED_END=$(TZ="Asia/Kolkata" date -d '+35 minutes' +"%Y-%m-%d %H:%M:%S")

      curl --silent --user "$SN_USER:$SN_PASS" -X PATCH \
        "https://$SN_INSTANCE/api/now/table/change_request/$SYS_ID" \
        -H "Content-Type: application/json" \
        -d "{
              \"start_date\": \"$SCHEDULED_START\",
              \"end_date\": \"$SCHEDULED_END\"
            }" > /dev/null

      echo "🕒 Scheduled Start (IST): $SCHEDULED_START" | tee -a "$LOG_FILE"
      echo "🕒 Scheduled End   (IST): $SCHEDULED_END" | tee -a "$LOG_FILE"
      CURRENT_START="$SCHEDULED_START"
    else
      echo "📅 Detected ServiceNow-scheduled Start Time: $CURRENT_START" | tee -a "$LOG_FILE"
    fi

    SCHEDULE_EPOCH=$(date -d "$CURRENT_START" +%s)
    NOW_EPOCH=$(date +%s)
    SLEEP_DURATION=$(( SCHEDULE_EPOCH - NOW_EPOCH ))

    if [ $SLEEP_DURATION -gt 0 ]; then
      echo "⏳ Waiting until scheduled start time: $SLEEP_DURATION seconds (Start: $CURRENT_START)" | tee -a "$LOG_FILE"
      sleep $SLEEP_DURATION
    else
      echo "⚠️ Start time already passed. Proceeding..." | tee -a "$LOG_FILE"
    fi

    WAITED_FOR_START=true
  fi

  if [[ "$CHANGE_STATE" == "-1" ]]; then
    echo "🚀 Change Request is now in 'Implement' state. Proceeding with deployment." | tee -a "$LOG_FILE"
    exit 0
  fi

  COUNT=$((COUNT+1))
  echo "⏳ Waiting... ($COUNT/$MAX_RETRIES)" | tee -a "$LOG_FILE"
  sleep $SLEEP_INTERVAL
done

echo "❌ Timeout: Change Request did not move to 'Implement' in time." | tee -a "$LOG_FILE"
exit 1
