//
//  FirstViewController.h
//  iAutohome
//
//  Created by Filip Sandborg-Olsen on 3/21/13.
//  Copyright (c) 2013 Filip Sandborg-Olsen. All rights reserved.
//

#import <UIKit/UIKit.h>
#import "NetworkConnection.h"

@interface FirstViewController : UIViewController <NetworkDelegate, UITableViewDelegate> {
    IBOutlet UITableView* table;
    NetworkConnection* conn;
}

@property (nonatomic, retain) UITableView* tableView;
@end
