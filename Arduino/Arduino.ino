#include <RemoteReceiver.h>
#include <RemoteTransmitter.h>
ElroTransmitter elroTransmitter(11);

void switcher(boolean state, int row) {
  if(!(row^0x7E)){
    digitalWrite(12, state?LOW:HIGH);
  } else if(!(row^0x7F)) {
    digitalWrite(13, state?LOW:HIGH);
  } else {
    elroTransmitter.sendSignal(31,'A'+row, state);
  }
}

void setup() {
  Serial.begin(9600);

  pinMode(12, OUTPUT);
  pinMode(13, OUTPUT);

  // PNP Transistors; HIGH is off
  digitalWrite(12, HIGH);
  digitalWrite(13, HIGH);
}


void loop() {
  if(Serial.available()>0) {
    char c = Serial.read();
    switcher((boolean)c>>7, (int)c&0x7F);
  }
}
