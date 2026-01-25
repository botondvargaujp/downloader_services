import requests
import requests
import json
import os
import shutil
from collections import defaultdict
from auth import get_token

# Position Mapping
POSITION_MAP = {
    "GK": "Goalkeeper",
    "CB": "Centre-Back",
    "LB": "Left-Back",
    "RB": "Right-Back",
    "DM": "Defensive-Midfield",
    "CM": "Central-Midfield",
    "AM": "Attacking-Midfield",
    "W":  "Winger",
    "F":  "Forward"
}

def get_token():

    email = 'varga.samu@ujpestfc.hu'
    password = 'Ujpest1885!'

    auth_url = 'https://apiprod.transferroom.com/api/external/login?email='+email+'&password='+password

    r = requests.post(auth_url)
    json_data = r.json()
    token = json_data['token']
    return token


print(get_token())
def get_full_position_name(pos_code):
    return POSITION_MAP.get(pos_code, pos_code)



def main():
    # Load filtered competitions mapping (Source of Truth for Tiers)
    print("Loading filtered competitions mapping...")
    valid_competition_ids = set()
    competition_map = {}
    
    try:
        with open('competitions.json', 'r', encoding='utf-8') as f:
            competitions_data = json.load(f)
            for comp in competitions_data:
                # Map ID to Name
                competition_map[comp['Id']] = comp['CompetitionName']
                # Filter: Tier <= 3
                tier = comp.get('DivisionLevel')
                if tier is not None and isinstance(tier, (int, float)) and tier <= 3:
                    valid_competition_ids.add(comp['Id'])
                    
    except FileNotFoundError:
        print("Error: filtered_competitions.json not found. Cannot filter by Tier.")
        return

    print(f"Loaded {len(valid_competition_ids)} valid competitions (Tier <= 3).")

    # Setup output directories
    primary_dir = os.path.join('data', 'primary_position_folders')
    secondary_dir = os.path.join('data', 'secondary_position_folders')
    
    # Clear existing directories to prevent duplication on re-runs
    if os.path.exists(primary_dir):
        shutil.rmtree(primary_dir)
    if os.path.exists(secondary_dir):
        shutil.rmtree(secondary_dir)
        
    os.makedirs(primary_dir, exist_ok=True)
    os.makedirs(secondary_dir, exist_ok=True)

    # Get authentication token
    token = get_token()
    headers = {"Authorization": "Bearer " + token}

    current_offset = 0
    amount = 10000
    more_players = True
    total_fetched = 0
    total_processed = 0
    
    # Track seen player IDs to prevent duplication
    seen_player_ids = set()

    print("Starting player fetch...")

    while more_players:
        request_url = f'https://apiprod.transferroom.com/api/external/players?position={current_offset}&amount={amount}'
        try:
            r = requests.get(request_url, headers=headers)
            r.raise_for_status()
            
            json_data = r.json()

            if isinstance(json_data, list):
                current_batch = json_data
            else:
                print("Unexpected response format.")
                break

            if not current_batch:
                more_players = False
                print("No more players to fetch.")
                break

            # Buffers for this batch
            batch_primary = defaultdict(list)
            batch_secondary = defaultdict(list)

            for player in current_batch:
                # Get Player ID for deduplication
                p_id = player.get('Id') or player.get('id')
                if not p_id:
                    # Fallback
                    p_id = str(player)
                
                if p_id in seen_player_ids:
                    continue
                seen_player_ids.add(p_id)

                # Filter by Competition Tier
                comp_id = player.get('CompetitionId') or player.get('competitionId')
                
                if comp_id is None:
                    continue
                
                if comp_id not in valid_competition_ids:
                    continue

                # Map Competition Name
                if comp_id in competition_map:
                    player['CompetitionName_Mapped'] = competition_map[comp_id]
                else:
                    player['CompetitionName_Mapped'] = f"Unknown Competition ({comp_id})"
                
                # Process Primary Position
                first_pos = player.get('FirstPosition')
                if first_pos:
                    full_name = get_full_position_name(first_pos)
                    batch_primary[full_name].append(player)
                
                # Process Secondary Position
                second_pos = player.get('SecondPosition')
                if second_pos:
                    full_name = get_full_position_name(second_pos)
                    batch_secondary[full_name].append(player)
                
                total_processed += 1

            # Write Primary Position files
            for pos, players in batch_primary.items():
                file_path = os.path.join(primary_dir, f"{pos}.json")
                with open(file_path, 'a', encoding='utf-8') as f:
                    for p in players:
                        json.dump(p, f, ensure_ascii=False)
                        f.write('\n')

            # Write Secondary Position files
            for pos, players in batch_secondary.items():
                file_path = os.path.join(secondary_dir, f"{pos}.json")
                with open(file_path, 'a', encoding='utf-8') as f:
                    for p in players:
                        json.dump(p, f, ensure_ascii=False)
                        f.write('\n')

            total_fetched += len(current_batch)
            print(f"Fetched {len(current_batch)} players. Processed {total_processed} valid unique players so far. Offset: {current_offset}")
            
            current_offset += amount

        except requests.exceptions.RequestException as e:
            print(f"Request failed: {e}")
            break
        except json.JSONDecodeError:
            print("Failed to decode JSON response")
            break
        except Exception as e:
            print(f"An error occurred: {e}")
            break
    
    print(f"Finished. Total valid players saved: {total_processed} (from {total_fetched} fetched).")
    print(f"Data partitioned in {primary_dir} and {secondary_dir}")

if __name__ == "__main__":
    main()
