//
//  NetworkConnection.m
//  iAutohome
//
//  Created by Filip Sandborg-Olsen on 3/21/13.
//  Copyright (c) 2013 Filip Sandborg-Olsen. All rights reserved.
//

#import "NetworkConnection.h"

@implementation NetworkConnection

enum {
    NoWork = 2,
    Work   = 3
};

-(id)init {
    self = [super init];
    [self startConnection];
    sendQueue = [[NSMutableArray alloc] init];
    queueLock = [[NSLock alloc] init];
    senderLock = [[NSConditionLock alloc] initWithCondition:NoWork];
    
    [NSThread detachNewThreadSelector:@selector(sendLoop) toTarget:self withObject:nil];
    return self;
}

-(void) sendCommand:(NSDictionary*)data {
    NSData* json = [NSJSONSerialization dataWithJSONObject:data options:NULL error:NULL];
    uint32_t length = [json length];
    length = (length << 24 & 0xFF000000) | (length << 8 & 0xFF0000) | (length >> 8 & 0xFF00) | (length >> 24 & 0xFF);
    uint32_t magic = 7U << 24 | 3U << 16 | 3U << 8 | 1U;
    uint8_t status = [output write: &magic maxLength: 4];
    if(status > 0) {
        [output write:(uint8_t*)&length maxLength:4];
        [NSJSONSerialization writeJSONObject:data toStream:output options:NULL error:NULL];
    }
    
//    int status;
//    do {
//        status = [output write:rawstr maxLength:strlen((char*) rawstr)];
//        if (status<0) {
//            [self startConnection];
//        }
//    } while (status < 0);
}

-(void) startConnection {
    CFWriteStreamRef write = NULL;
    CFReadStreamRef read = NULL;
    
    NSString *host = @"10.0.1.45";
    int port = 9993;
    CFStreamCreatePairWithSocketToHost(kCFAllocatorDefault, (__bridge CFStringRef)host, port, &read, &write);
    if (!write) {
        // connection failed.
        NSLog(@"Connection to %@:%d failed.",host,port);
    } else {
        CFWriteStreamOpen(write);
        CFReadStreamOpen(read);
        output = (__bridge_transfer NSOutputStream*)write;
        input = (__bridge_transfer NSInputStream*)read;
        [input setDelegate:self];
        [output setDelegate:self];
        [input scheduleInRunLoop:[NSRunLoop currentRunLoop] forMode:NSDefaultRunLoopMode];
        [output scheduleInRunLoop:[NSRunLoop currentRunLoop] forMode:NSDefaultRunLoopMode];
        [output open];
        [input open];
    }
}

-(void) addToQueue:(NSDictionary*)element {
    [queueLock lock];
    [sendQueue addObject:element];
    [queueLock unlock];
    [senderLock unlockWithCondition:Work];
}

-(void) sendLoop {
    while(1) {
        [senderLock lockWhenCondition:Work];
        NSDictionary *sendObj;
        
        while ([sendQueue count] > 0) {
            [queueLock lock];
            sendObj = [sendQueue objectAtIndex:0];
            [sendQueue removeObjectAtIndex:0];
            [queueLock unlock];
            
            [self sendCommand:sendObj];
        }
        [senderLock unlockWithCondition:NoWork];
    }
}

-(void) stream: (NSInputStream *) iStream handleEvent: (NSStreamEvent)event {
    BOOL shouldClose = NO;
    switch (event) {
        case NSStreamEventEndEncountered:
        {
            shouldClose = YES;
            if(![iStream hasBytesAvailable]) break;
        }
        case NSStreamEventHasBytesAvailable: ;
        {
            NSMutableData *data=[[NSMutableData alloc] init];
            uint8_t *buffer;
            NSUInteger length;
            BOOL freeBuffer = NO;
            buffer = malloc(1024 * sizeof(uint8_t));
            if(![iStream getBuffer:&buffer length:&length]) {
                freeBuffer = YES;
                NSInteger result = [iStream read:buffer maxLength:1024];
                if(result < 0) {
                    break;
                }
                length = result;
                [data appendBytes:buffer length:length];
                if (length>8) {
                    [data replaceBytesInRange:NSMakeRange(0, 8) withBytes:NULL length:0];
                    NSDictionary* jsonobj = [NSJSONSerialization JSONObjectWithData:data options:nil error:nil];
                    if (jsonobj != nil) {
                        [[self delegate] handleEvent:jsonobj];
                    }
                }
            }
            if(freeBuffer) free(buffer);
            break;
        }
        case NSStreamEventErrorOccurred:
        {
            shouldClose = YES;
            break;
        }
    }
    if(shouldClose) {
        [input close];
        [output close];
        [self startConnection];
    }
}

-(void) close {
    [output close];
    [input close];
}
@end
