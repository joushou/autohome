void clearStates() {
  for(int i = 2; i <= 8; ++i) {
    pinMode(i, INPUT);
    digitalWrite(i, LOW);
  }
}

void switcher(boolean state, int row) {
  if(!(row^0x7F)){
    digitalWrite(13, state?HIGH:LOW);
  } else {
    clearStates();
    pinMode((state)?3:2, OUTPUT);
    digitalWrite((state)?3:2, LOW);
    pinMode(row+4, OUTPUT);
    digitalWrite(row+4, LOW);
    delay(300);
    clearStates();
    delay(300);
  }
}

void setup() {
  clearStates();
  Serial.begin(9600);
}


void loop() {
  if(Serial.available()>0) {
    char c = Serial.read();
    switcher((boolean)c>>7, (int)c&0x7F);
  }
}
