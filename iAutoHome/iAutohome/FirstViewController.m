//
//  FirstViewController.m
//  iAutohome
//
//  Created by Filip Sandborg-Olsen on 3/21/13.
//  Copyright (c) 2013 Filip Sandborg-Olsen. All rights reserved.
//

#import "FirstViewController.h"

@interface FirstViewController () {
    NSMutableArray* _objects;
}
@end

@implementation FirstViewController


- (void)viewDidLoad
{
    [super viewDidLoad];
}
-(void) viewWillAppear:(BOOL)animated {
    conn = [[NetworkConnection alloc] init];
    [conn setDelegate:self];
    [conn addToQueue:[[NSDictionary alloc] initWithObjectsAndKeys:@"list",@"op", nil]];
}
-(void) viewDidDisappear:(BOOL)animated {
    [conn close];
}

- (void)didReceiveMemoryWarning
{
    [super didReceiveMemoryWarning];
    // Dispose of any resources that can be recreated.
}


-(void) switchToggled:(UISwitch*) sw {
    NSString *deviceName = [[_objects objectAtIndex:sw.tag] objectForKey:@"title"];
    if(sw.on) {
        NSLog(@"Turned device '%@' on.", deviceName);
        NSDictionary *cmd = [[NSDictionary alloc] initWithObjectsAndKeys:@"on",@"op",deviceName,@"name", nil];
        [[_objects objectAtIndex:sw.tag] setObject:@"on" forKey:@"state"];
        [conn addToQueue: cmd];
    } else {
        NSLog(@"Turned device '%@' off.", deviceName);
        NSDictionary *cmd = [[NSDictionary alloc] initWithObjectsAndKeys:@"off",@"op",deviceName,@"name", nil];
        [[_objects objectAtIndex:sw.tag] setObject:@"off" forKey:@"state"];
        [conn addToQueue:cmd];
    }
}
-(void) handleEvent:(NSDictionary*)ev {
    NSLog(@"%@", ev);
    if ([ev objectForKey:@"status"] == nil) {
        [_objects removeAllObjects];
        for(NSString* key in ev) {
            [self insertNewObject:self withLabel:[[NSMutableDictionary alloc] initWithObjectsAndKeys:key, @"title", [[ev objectForKey:key] objectForKey:@"state"], @"state", nil]];
        }
    }
    [table reloadData];
}



-(void)insertNewObject:(id)sender withLabel:(NSDictionary *) obj {
    if(!_objects) {
        _objects = [[NSMutableArray alloc] init];
    }
    [_objects addObject:obj];
    //[self.tableView reloadData];
    //NSIndexPath *indexPath = [NSIndexPath indexPathForRow:[_objects count]-1 inSection:0];
    //[self.tableView insertRowsAtIndexPaths:@[indexPath] withRowAnimation:UITableViewRowAnimationAutomatic];
}
#pragma mark - Table View

- (NSInteger)numberOfSectionsInTableView:(UITableView *)tableView
{
    return 1;
}

- (NSInteger)tableView:(UITableView *)tableView numberOfRowsInSection:(NSInteger)section
{
    return _objects.count;
}

- (UITableViewCell *)tableView:(UITableView *)tableView cellForRowAtIndexPath:(NSIndexPath *)indexPath
{
    UITableViewCell *cell = [tableView dequeueReusableCellWithIdentifier:@"deviceListCell"];
    if (cell == nil)
    {
        cell = [[UITableViewCell alloc] initWithStyle:UITableViewCellStyleDefault
                                      reuseIdentifier:@"deviceListCell"];
    }
    
    CGRect frameSwitch = CGRectMake(215.0, 10.0, 94.0, 27.0);
    UISwitch *switchEnabled = [[UISwitch alloc] initWithFrame:frameSwitch];
    [switchEnabled addTarget:self action:@selector(switchToggled:) forControlEvents:UIControlEventValueChanged];
    NSDictionary *object = [_objects objectAtIndex:indexPath.row];
    
    if ([[object objectForKey:@"state"] isEqualToString: @"on"]) {
        [switchEnabled setOn:YES];
    } else {
        [switchEnabled setOn:NO];
    }
    switchEnabled.tag = indexPath.row;
    
    cell.accessoryView = switchEnabled;

    cell.textLabel.text = [object objectForKey:@"title"];
    
    return cell;
}

- (BOOL)tableView:(UITableView *)tableView canEditRowAtIndexPath:(NSIndexPath *)indexPath
{
    // Return NO if you do not want the specified item to be editable.
    return NO;
}

- (void)tableView:(UITableView *)tableView commitEditingStyle:(UITableViewCellEditingStyle)editingStyle forRowAtIndexPath:(NSIndexPath *)indexPath
{
    if (editingStyle == UITableViewCellEditingStyleDelete) {
        [_objects removeObjectAtIndex:indexPath.row];
        [tableView deleteRowsAtIndexPaths:@[indexPath] withRowAnimation:UITableViewRowAnimationFade];
    } else if (editingStyle == UITableViewCellEditingStyleInsert) {
        // Create a new instance of the appropriate class, insert it into the array, and add a new row to the table view.
    }
}


@end
