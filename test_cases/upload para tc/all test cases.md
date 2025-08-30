1. ### **Success Cases**



***01: Add a new parameter to an existing flight***



Pre: F001\_user1 exists (uploaded from TC1\_valid\_user1.csv).



Action:



Flight ID: F001\_user1



Parameter Name: Angle\_of\_Attack



Parameter Value: 5.2



Click Submit Parameter



Expected: Success toast. In View Data, you’ll see Angle\_of\_Attack: 5.2.







***02: Update an existing parameter***



Pre: F001\_user1 has Angle\_of\_Attack: 5.2.



Action:



Flight ID: F001\_user1



Parameter Name: Angle\_of\_Attack



Parameter Value: 7.8



Click Update Parameter



Expected: Success; new value shows as 7.8.





***03 : Delete a parameter***



Pre: F001\_user1 has Angle\_of\_Attack.



Action:



Flight ID: F001\_user1



Parameter Name: Angle\_of\_Attack



Click Delete Parameter



Expected: Success; field disappears from View Data.





04: FlightID auto-append suffix



Action:



Flight ID: F999 (no suffix)



Parameter Name: Note



Parameter Value: Test



Submit



Expected: Component auto-converts to F999\_user1 and proceeds.



## 2\. **Failure Cases**



***05: Wrong user’s suffix***



Action:



Flight ID: F001\_user2 while logged in as user1@gmail.com



Expected: UI warning: “FlightID must end with \_user1”. Backend would 404 (not found for this user).







***06: Update non-existent parameter***



Action:



Flight ID: F001\_user1



Parameter Name: NonExistentParam



Parameter Value: 123



Click Update Parameter



Expected: Backend 404 “Parameter or Flight ID not found”. (So use Submit Parameter first.)







