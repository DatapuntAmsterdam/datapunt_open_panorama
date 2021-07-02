## Blurren CTO gedetecteerde panorama's

Dit beschrijft  de stappen die genomen moeten worden om panorama's te blurren waarvoor CTO de detectie heeft gedaan van 
de personen en nummerborden.

Dit is nu al gebeurt voor het jaar 2020.


Eerst moet CTO de detectie doen. Rechtgezette panorama's uit de intermediate directory worden naar Azure gekopieerd. 
Daar start CTO het detectie process en de gedetecteerde vierkanten worden opgeslagen in CSV files met hetzelfde 
formaat als de panoramas_region tabel.

Die CSV files werden teruggestuurd en hadden namen pano_meta_01.txt t/m pano_meta_12.txt

Het blur- (en detectie) in cloudvps bestaat uit een aantal stappen die beschreven staan in :

https://wiki.data.amsterdam.nl/doku.php?id=start:datasets:kernregistratie:pano:verw&s[]=swarm


Dan moeten eerst stap 2 en 3 zijn uitgevoerd. De swarm moet gestart zijn en de tijdelijke database op 
master.swarm.data.amsterdam.nl zijn op gebracht. 

Via de VPN kun je direct met deze database vebinden. Host is tot nu toe altijd  10.243.16.22
user en database panorama.

Om het bijgesloten script load_cto_regions.sh te draaien moeten de omgevings variabelen voor de Postgres 
database worden gezet. Eigenlijk alleen PGHOSTADDR.

Het script leest de CSV files, zet ze in een tijdelijke tabel. Kopieert de tijdelijk tabel naar panoramas_region region 
tabel. Vervolgens worden alle panorama's met door CTO toegevoegde regionen op status 'detected' gezet. 

Als dit gaat gebeuren voor 2019 of 2021 ofzo dan moet er een extra conditie met bij komen dat niet 2020 ook opnieuw op 
detected wordt gezet, anders wordt ook 2020 opnieuw gedaan.   

Zodra de status op detected staat zullen de workers van de swarm dit oppikken opnieuw gaan blurren.
Voor heel 2020  (800000 plus panorama's) duurde dit iets meer dan een week.

Als alles klaar is kan stap 4, het stoppen van de verwerking, worden uitgevoerd. Dwz. export van regions tabel.
Import van de regions in productiedb en daarna stoppen van de swarm  

Als je dit alles eerst lokaal wil testen dan is het belangrijk dat hij de geblurde files niet terugschrijft 
naar de objectstore. In deze branch bart/cto_test is een wijziging  in web/panorama/panorama/transform/utils_img_file.py
dat de files alleen lokaal ergens worden weggeschreven als een worker wordt opgestart. 

