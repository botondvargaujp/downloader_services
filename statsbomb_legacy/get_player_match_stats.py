from statsbombpy import sb


creds = {"user": "botond.varga.ujp@gmail.com", "passwd": "AYHQhWwK"}
events = sb.events(match_id=4003652, creds=creds)
print(events.shape)
for i in range(0,len(events.columns),25):
    print(events.columns[i:i+25])

    