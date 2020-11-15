from django.db import models

# Create your models here.

class Station(models.Model):
    station_no = models.IntegerField()
    station_id = models.CharField(max_length=30,primary_key=True)
    name = models.CharField(max_length=100)
    area_id = models.CharField(max_length=4)
    area_name = models.CharField(max_length=30)
    region = models.CharField(max_length=30)

class Program(models.Model):
    id = models.IntegerField(primary_key=True)
    station_id = models.CharField(max_length=30)
    station_name = models.CharField(max_length=100)
    date = models.CharField(max_length=8)
    title = models.CharField(max_length=100)
    failed_record = models.CharField(max_length=1)
    desc = models.CharField(max_length=2000, null=True)
    info = models.CharField(max_length=2000, null=True)
    pfm = models.CharField(max_length=200, null=True)
    prog_id = models.CharField(max_length=10)
    ft = models.CharField(max_length=14)
    to = models.CharField(max_length=14)
    dur = models.CharField(max_length=14)
    download = models.IntegerField()
    
    class Meta:
        unique_together=('station_id', 'prog_id')


