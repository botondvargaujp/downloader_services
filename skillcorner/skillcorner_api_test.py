import skillcorner

from skillcorner.client import SkillcornerClient

client = SkillcornerClient(username='botond.varga16@gmail.com', password='Dobocsillag10!')


seasons = client.get_seasons()
print(len(seasons))
