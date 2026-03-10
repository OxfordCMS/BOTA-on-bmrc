#!/usr/bin/env python3
"""
gff_to_faa.py

Pre-generate .faa and .ffn files from a GFF + FNA for use with BOTA.
Designed for MAGs where BOTA's internal prodigal step fails due to
non-standard contig headers.

Usage:
    python3 gff_to_faa.py --fna genome.fna --gff genome.gff \
                          --genome SAMPLE_NAME --outdir /path/to/output
"""

from Bio import SeqIO
from Bio.Seq import Seq
import os
import argparse


def parse_attrs(attr_str):
    d = {}
    for chunk in attr_str.strip().split(';'):
        if not chunk:
            continue
        if '=' in chunk:
            k, v = chunk.split('=', 1)
            d[k] = v
    return d


def gff_to_faa(fna, gff, genome, outdir, translation_table=11):
    genome_dir = os.path.join(outdir, genome)
    os.makedirs(genome_dir, exist_ok=True)

    out_faa = os.path.join(genome_dir, '%s.faa' % genome)
    out_ffn = os.path.join(genome_dir, '%s.ffn' % genome)

    # Load all contig sequences
    seqs = {}
    for rec in SeqIO.parse(fna, 'fasta'):
        seqs[rec.id] = str(rec.seq)
        if rec.name != rec.id:
            seqs[rec.name] = str(rec.seq)

    cds_entries = []
    with open(gff) as gh:
        for line in gh:
            if line.startswith('#'):
                continue
            parts = line.rstrip().split('\t')
            if len(parts) < 9:
                continue
            contig, source, ftype, start_s, end_s, score, strand, phase, attrs = parts[:9]
            if ftype != 'CDS':
                continue
            try:
                start = int(start_s)
                end   = int(end_s)
            except ValueError:
                continue
            attrd  = parse_attrs(attrs)
            parent = (attrd.get('Parent') or attrd.get('ID') or
                      attrd.get('gene') or '%s_%s_%s' % (contig, start, end))
            if contig not in seqs:
                raise SystemExit('Contig %s from GFF not found in FASTA.' % contig)
            nt = seqs[contig][start - 1:end]
            if strand == '-':
                nt_seq = str(Seq(nt).reverse_complement())
            else:
                nt_seq = nt
            aa = str(Seq(nt_seq).translate(table=translation_table, to_stop=False))
            aa = aa.replace('*', '')
            tag = '%s|%s-%s|%s' % (contig, start, end, strand)
            cds_entries.append((parent, tag, aa, nt_seq))

    if len(cds_entries) == 0:
        raise SystemExit('No CDS entries parsed from GFF: %s' % gff)

    with open(out_faa, 'w') as fa_fh, open(out_ffn, 'w') as ffn_fh:
        for parent, tag, aa_seq, nt_seq in cds_entries:
            xtag = '%s|gene=%s' % (tag, parent)
            fa_fh.write('>%s\n' % xtag)
            for i in range(0, len(aa_seq), 60):
                fa_fh.write(aa_seq[i:i + 60] + '\n')
            ffn_fh.write('>%s\n' % xtag)
            for i in range(0, len(nt_seq), 60):
                ffn_fh.write(nt_seq[i:i + 60] + '\n')

    print('Wrote %s (%d CDS)' % (out_faa, len(cds_entries)))
    print('Wrote %s' % out_ffn)
    return out_faa, out_ffn


def main():
    parser = argparse.ArgumentParser(
        description='Pre-generate .faa/.ffn from GFF+FNA for BOTA MAG analysis')
    parser.add_argument('--fna',    required=True, help='Input genome FASTA (.fna)')
    parser.add_argument('--gff',    required=True, help='Input annotation (.gff)')
    parser.add_argument('--genome', required=True, help='Sample/genome name (used for output filenames)')
    parser.add_argument('--outdir', required=True, help='Output root directory')
    parser.add_argument('--table',  type=int, default=11,
                        help='Translation table (default: 11 for bacteria/archaea)')
    args = parser.parse_args()

    gff_to_faa(
        fna=args.fna,
        gff=args.gff,
        genome=args.genome,
        outdir=args.outdir,
        translation_table=args.table
    )


if __name__ == '__main__':
    main()
