#include <Wire.h>
#include <Adafruit_PWMServoDriver.h>

Adafruit_PWMServoDriver pwm = Adafruit_PWMServoDriver(0x40);

#define SERVOMIN  125 // Min pulse length out of 4096 (~0 deg)
#define SERVOMAX  575 // Max pulse length out of 4096 (~180 deg)
#define SERVO_FREQ 50 // 50Hz analog servos

const int NUM_SERVOS = 6;
// Target and current angles for: Base, Shoulder, Elbow, WristRot, WristTilt, Gripper
float currentAngles[NUM_SERVOS] = {90.0, 90.0, 90.0, 90.0, 90.0, 90.0};
float targetAngles[NUM_SERVOS]  = {90.0, 90.0, 90.0, 90.0, 90.0, 90.0};

const byte numChars = 64;
char receivedChars[numChars];
boolean newData = false;

int angleToPulse(float angle) {
  angle = constrain(angle, 0.0, 180.0);
  return map((int)angle, 0, 180, SERVOMIN, SERVOMAX);
}

void setServoAngle(uint8_t n, float angle) {
  pwm.setPWM(n, 0, angleToPulse(angle));
}

void setup() {
  Serial.begin(115200);
  pwm.begin();
  pwm.setPWMFreq(SERVO_FREQ);
  delay(500);

  // Initialize all servos to 90 degrees
  for (int i = 0; i < NUM_SERVOS; i++) {
    setServoAngle(i, currentAngles[i]);
  }
  Serial.println("READY");
}

void recvWithStartEndMarkers() {
  static boolean recvInProgress = false;
  static byte ndx = 0;
  char startMarker = '<';
  char endMarker = '>';
  char rc;

  while (Serial.available() > 0 && newData == false) {
    rc = Serial.read();

    if (recvInProgress == true) {
      if (rc != endMarker) {
        receivedChars[ndx] = rc;
        ndx++;
        if (ndx >= numChars) {
          ndx = numChars - 1;
        }
      } else {
        receivedChars[ndx] = '\0';
        recvInProgress = false;
        ndx = 0;
        newData = true;
      }
    } else if (rc == startMarker) {
      recvInProgress = true;
    }
  }
}

void parseData() {
  char *strtokIndx;
  strtokIndx = strtok(receivedChars, ",");
  int idx = 0;

  while (strtokIndx != NULL && idx < NUM_SERVOS) {
    targetAngles[idx] = atof(strtokIndx);
    targetAngles[idx] = constrain(targetAngles[idx], 0.0, 180.0);
    strtokIndx = strtok(NULL, ",");
    idx++;
  }
}

void updateServos() {
  const float step = 1.5; // Max degrees moved per update tick
  for (int i = 0; i < NUM_SERVOS; i++) {
    if (abs(currentAngles[i] - targetAngles[i]) > 0.5) {
      if (currentAngles[i] < targetAngles[i]) {
        currentAngles[i] = min(currentAngles[i] + step, targetAngles[i]);
      } else {
        currentAngles[i] = max(currentAngles[i] - step, targetAngles[i]);
      }
      setServoAngle(i, currentAngles[i]);
    }
  }
}

void loop() {
  recvWithStartEndMarkers();
  if (newData) {
    parseData();
    newData = false;
    Serial.println("ACK");
  }
  updateServos();
  delay(15); // ~66Hz loop refresh for smooth interpolation
}