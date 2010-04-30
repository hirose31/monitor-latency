#!/usr/bin/env perl

use strict;
use warnings;
use Data::Dumper;
$Data::Dumper::Indent   = 1;
$Data::Dumper::Deepcopy = 1;
$Data::Dumper::Sortkeys = 1;
use IO::File;
STDOUT->autoflush(1);
STDERR->autoflush(1);

use Sys::Hostname;
use CGI qw(:standard);
use CGI::Carp qw(fatalsToBrowser);

my $Debug = 0;

sub pp(@) {
    my $d = Dumper(\@_);
    $d =~ s/\\x{([0-9a-z]+)}/chr(hex($1))/ge;
    print STDERR $d;
}

my $RRD_Dir = param("r") || $ENV{"RRD_DIR"} or croak "missing: r (RRD_DIR)";
croak "missing: n" unless param("n");

$Debug = param("debug") if param("debug");

my $rrdfile = sprintf("%s/%s.rrd", $RRD_Dir, param("n") );
croak "cannot read rrdfile: $rrdfile" unless -r $rrdfile;

print header(-type => $Debug ? "text/plain" : "image/png", -expires => '-1h' );
print_graph(
    name  => param("n"),
    rrd   => $rrdfile,
    start => param("s")||"",
    end   => param("e")||"",
    draw_packet_loss => param("np") ? 0 : 1,
   );
exit;

sub print_graph {
    my %param = @_;

    $param{start}  ||= "-24h";
    $param{end}    ||= "NOW";

    $param{width}  ||= "480";
    $param{height} ||= "128";

    $param{extra_args} ||= "";

    if ($param{end} eq "NOW") {
        foreach ($param{start}) {
            # /-1h/ and do { $param{extra_args} .= q{ }; last; };
            # /-6h/ and do { $param{extra_args} .= q{ }; last; };
            # /-12h/ and do { $param{extra_args} .= q{ }; last; };
            /-1d/ and do { $param{extra_args} .= q{ --x-grid HOUR:1:HOUR:3:HOUR:3:0:'%H:%M'}; last; };
            /-3d/ and do { $param{extra_args} .= q{ --x-grid HOUR:3:HOUR:6:HOUR:12:0:'%a %H'}; last; };
            # /-1w/ and do { $param{extra_args} .= q{ }; last; };
            # /-1m/ and do { $param{extra_args} .= q{ }; last; };
            # /-1y/ and do { $param{extra_args} .= q{ }; last; };
        }
    }


    my $cmd =<<'EOCMD';
rrdtool graph - \
  -s "@@start@@" -e "@@end@@" \
  -t "ping rtt: @@name@@" \
  -w @@width@@ -h @@height@@ \
  --slope \
  @@extra_args@@ \
  DEF:pkt_loss_r=@@rrd@@:pkt_loss:MAX \
  DEF:rtt_min_r=@@rrd@@:rtt_min:MAX \
  DEF:rtt_avg_r=@@rrd@@:rtt_avg:MAX \
  DEF:rtt_max_r=@@rrd@@:rtt_max:MAX \
  DEF:rtt_mdev_r=@@rrd@@:rtt_mdev:MAX \
  CDEF:rtt_max=rtt_max_r,1000,/,0,0.400,LIMIT \
  CDEF:rtt_avg=rtt_avg_r,1000,/,0,0.400,LIMIT \
  CDEF:rtt_min=rtt_min_r,1000,/,0,0.400,LIMIT \
  VDEF:rtt_min_last=rtt_min,LAST \
  VDEF:rtt_avg_last=rtt_avg,LAST \
  VDEF:rtt_max_last=rtt_max,LAST \
  VDEF:rtt_span_min=rtt_min,MINIMUM \
  VDEF:rtt_span_avg=rtt_avg,AVERAGE \
  VDEF:rtt_span_max=rtt_max,MAXIMUM \
  VDEF:pkt_loss_max=pkt_loss_r,MAXIMUM \
  CDEF:pkt_loss_min_r=pkt_loss_r,1,INF,LIMIT \
  VDEF:pkt_loss_min=pkt_loss_min_r,MINIMUM \
  CDEF:pkt_loss=rtt_span_max,pkt_loss_r,*,30,/ \
  AREA:rtt_max#CFE5FF \
  AREA:rtt_min#FFFFFF \
  LINE1:rtt_avg#001D3F \
  COMMENT:'Now             \: \g' \
  GPRINT:rtt_min_last:'%7.3lf%S /\g' \
  GPRINT:rtt_avg_last:'%7.3lf%S /\g' \
  GPRINT:rtt_max_last:'%7.3lf%S (min/avg/max)\l' \
  COMMENT:'Displayed period\: \g' \
  GPRINT:rtt_span_min:'%7.3lf%S /\g' \
  GPRINT:rtt_span_avg:'%7.3lf%S /\g' \
  GPRINT:rtt_span_max:'%7.3lf%S\l' \
EOCMD
    if ($param{draw_packet_loss}) {
        $cmd .=<<'EOCMD'
  LINE1:pkt_loss#FF0000:'packet loss   \:\g' \
  GPRINT:pkt_loss_min:'%3.0lf%% /\g' \
  GPRINT:pkt_loss_max:'%3.0lf%% (min/max),' \
  HRULE:rtt_span_max#5e0e33:'\: packet loss 30%\l':dashes=3 \
EOCMD
    }
    $cmd .= ";";

    $cmd =~ s/@@([^@]+?)@@/$param{$1}/ge;

    print $Debug ? qq{$cmd} : qx{$cmd};;
}


__END__

QUERY_STRING:

r=RRD_DIR
n=RRD_LABEL
s=START
e=END
debug=1

?r=/var/rrd&n=google&s=-1d

# for Emacsen
# Local Variables:
# mode: cperl
# cperl-indent-level: 4
# indent-tabs-mode: nil
# coding: utf-8
# End:

# vi: set ts=4 sw=4 sts=0 :
