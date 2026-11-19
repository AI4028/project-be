# Catalog photos

The menu JPEGs in `seed/menu-photos/` bootstrap fresh S3 buckets and support local
demos. Staff can replace menu photos from the kiosk once S3 is enabled. See
[deployment setup](../docs/production-deployment.md#enable-menu-photo-uploads-on-ec2).

Store photos and legacy local images are served at their database paths under
`/media/`. Both store and menu records also accept full HTTPS image URLs.
