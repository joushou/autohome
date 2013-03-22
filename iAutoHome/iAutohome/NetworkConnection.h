//
//  NetworkConnection.h
//  iAutohome
//
//  Created by Filip Sandborg-Olsen on 3/21/13.
//  Copyright (c) 2013 Filip Sandborg-Olsen. All rights reserved.
//

#import <Foundation/Foundation.h>



@protocol NetworkDelegate <NSObject>
@required
-(void) handleEvent : (NSDictionary*) event;
@end

@interface NetworkConnection : NSObject <NSStreamDelegate> {
    NSOutputStream *output;
    NSInputStream *input;
    NSMutableArray *sendQueue;
    NSLock *queueLock;
    NSConditionLock *senderLock;
}
-(void) close;
-(void) sendCommand:(NSDictionary*)data;
-(void) addToQueue:(NSDictionary*)element;
@property (nonatomic, assign) id <NetworkDelegate> delegate;
@end
