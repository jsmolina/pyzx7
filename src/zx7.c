/*
 * (c) Copyright 2012 by Einar Saukas. All rights reserved.
 *
 * Redistribution and use in source and binary forms, with or without
 * modification, are permitted provided that the following conditions are met:
 *     * Redistributions of source code must retain the above copyright
 *       notice, this list of conditions and the following disclaimer.
 *     * Redistributions in binary form must reproduce the above copyright
 *       notice, this list of conditions and the following disclaimer in the
 *       documentation and/or other materials provided with the distribution.
 *     * The name of its author may not be used to endorse or promote products
 *       derived from this software without specific prior written permission.
 *
 * THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
 * ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
 * WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
 * DISCLAIMED. IN NO EVENT SHALL <COPYRIGHT HOLDER> BE LIABLE FOR ANY
 * DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
 * (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
 * LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND
 * ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
 * (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
 * SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
 */

#include <stdio.h>
#include <stdlib.h>
#include <string.h>

#include "zx7.h"

int comp(char *filename) {
    FILE *ifp;
    FILE *ofp;
    unsigned char *input_data;
    unsigned char *output_data;
    size_t input_size;
    size_t output_size;
    size_t partial_counter;
    size_t total_counter;
    char *output_name;

    /* determine output filename */
    output_name = (char *)malloc(strlen(filename)+5);
    strcpy(output_name, filename);
    strcat(output_name, ".zx7");

    /* open input file */
    ifp = fopen(filename, "rb");
    if (!ifp) {
         fprintf(stderr, "Error: Cannot access input file %s\n", filename);
         return 1;
    }

    /* determine input size */
    fseek(ifp, 0L, SEEK_END);
    input_size = ftell(ifp);
    fseek(ifp, 0L, SEEK_SET);
    if (!input_size) {
         fprintf(stderr, "Error: Empty input file %s\n", filename);
         return 1;
    }

    /* allocate input buffer */
    input_data = (unsigned char *)malloc(input_size);
    if (!input_data) {
         fprintf(stderr, "Error: Insufficient memory\n");
         return 1;
    }

    /* read input file */
    total_counter = 0;
    do {
        partial_counter = fread(input_data+total_counter, sizeof(char), input_size-total_counter, ifp);
        total_counter += partial_counter;
    } while (partial_counter > 0);

    if (total_counter != input_size) {
         fprintf(stderr, "Error: Cannot read input file %s\n", filename);
         return 1;
    }

    /* close input file */
    fclose(ifp);

    /* check output file */
    if (fopen(output_name, "rb") != NULL) {
         fprintf(stderr, "Error: Already existing output file %s\n", output_name);
         return 1;
    }

    /* create output file */
    ofp = fopen(output_name, "wb");
    if (!ofp) {
         fprintf(stderr, "Error: Cannot create output file %s\n", output_name);
         return 1;
    }

    /* generate output file */
    output_data = compress(optimize(input_data, input_size), input_data, input_size, &output_size);

    /* write output file */
    if (fwrite(output_data, sizeof(char), output_size, ofp) != output_size) {
         fprintf(stderr, "Error: Cannot write output file %s\n", output_name);
         return 1;
    }

    /* close output file */
    fclose(ofp);

    /* done! */
    printf("Optimal LZ77/LZSS compression by Einar Saukas\nFile converted from %lu to %lu bytes!\n",
        (unsigned long)input_size, (unsigned long)output_size);

    return 0;
}
