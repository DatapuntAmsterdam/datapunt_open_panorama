from math import atan2, degrees, cos, sin, radians
from django.contrib.gis.db import models as geo
from django.db import models
from django.contrib.gis.geos import Point
# Project
from panorama.settings import PANO_DIR, PANO_IMAGE_URL


class Panorama(models.Model):
    id = models.AutoField(primary_key=True)
    pano_id = models.CharField(max_length=37, unique=True)
    timestamp = models.DateTimeField()
    filename = models.CharField(max_length=255)
    path = models.CharField(max_length=400)
    geolocation = geo.PointField(dim=3, srid=4326, spatial_index=True)
    _geolocation_2d = geo.PointField(dim=2, srid=4326, spatial_index=True)
    roll = models.FloatField()
    pitch = models.FloatField()
    heading = models.FloatField()
    adjacent_panos = models.ManyToManyField('self', through='Adjacency', symmetrical=False)

    objects = geo.GeoManager()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self._geolocation_2d:
            self._derive_calculated_fields()

    def _derive_calculated_fields(self):
        self._geolocation_2d = Point(self.geolocation[0], self.geolocation[1])

    def save(self, *args, **kwargs):
        self._derive_calculated_fields()
        super().save(*args, **kwargs)

    def __str__(self):
        return '<Panorama %s/%s>' % (self.path, self.filename)

    @property
    def img_url(self):
        return '%s%s/%s' % (
            PANO_IMAGE_URL, self.path.replace(PANO_DIR, ''), self.filename)


class Adjacency(models.Model):
    from_pano = models.ForeignKey(Panorama, related_name='to_adjacency')
    to_pano = models.ForeignKey(Panorama,  related_name='from_adjacency')
    direction = models.FloatField()
    heading = models.DecimalField(max_digits=20, decimal_places=2)
    distance = models.FloatField()
    elevation = models.FloatField()

    class Meta:
        managed = False
        db_table = "panoramas_adjacencies"

    def __str__(self):
        return '<Adjacency %s -> /%s>' % (self.from_pano_id, self.to_pano_id)

    @property
    def direction(self):
        return (self.heading - self.from_pano.heading) % 360

    @property
    def angle(self):
        cam_angle = self.from_pano.pitch*cos(radians(self.direction)) \
                    - self.from_pano.roll*sin(radians(self.direction))
        return self.pitch - cam_angle

    @property
    def pitch(self):
        if not self.elevation or self.distance <= 0.0:
            return 0.0
        else:
            return degrees(atan2(self.elevation, self.distance))

class Traject(models.Model):
    timestamp = models.DateTimeField()
    geolocation = geo.PointField(dim=3, spatial_index=True)
    north_rms = models.DecimalField(
        max_digits=20, decimal_places=14)
    east_rms = models.DecimalField(
        null=True, blank=True, max_digits=20, decimal_places=14)
    down_rms = models.DecimalField(
        null=True, blank=True, max_digits=20, decimal_places=14)
    roll_rms = models.FloatField(null=True, blank=True)
    pitch_rms = models.FloatField(null=True, blank=True)
    heading_rms = models.FloatField(null=True, blank=True)

    objects = geo.GeoManager()

    def __str__(self):
        return '<Traject %d>' % self.pk
