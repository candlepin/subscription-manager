const path = require("path");
const copy = require("copy-webpack-plugin");
const fs = require("fs");
const TerserJSPlugin = require('terser-webpack-plugin');
const CssMinimizerPlugin = require('css-minimizer-webpack-plugin');
const webpack = require("webpack");
const CompressionPlugin = require("compression-webpack-plugin");
const ESLintPlugin = require('eslint-webpack-plugin');
const glob = require("glob");
const po2json = require("po2json");
const miniCssExtractPlugin = require('mini-css-extract-plugin');

var externals = {
    "cockpit": "cockpit",
};

/* These can be overridden, typically from the Makefile.am */
const srcdir = (process.env.SRCDIR || __dirname) + path.sep + "src";
const builddir = (process.env.SRCDIR || __dirname);
const distdir = builddir + path.sep + "dist";
const section = process.env.ONLYDIR || null;
const nodedir = path.relative(process.cwd(), path.resolve(builddir, "node_modules"));
const libdir = srcdir + path.sep + "lib";

/* A standard nodejs and webpack pattern */
var production = process.env.NODE_ENV === 'production';

var info = {
    entries: {
        "index": [
            "./index.js",
        ],
    },
    files: [
        "index.html",
        "manifest.json",
        "po.js",
    ],
};

if (!production) {
    info.entries["dbus-testing"] = [
      "spec/dbus/dbus.test.js"
    ]
}

var output = {
    path: distdir,
    filename: "[name].js",
    sourceMapFilename: "[file].map",
};

/*
 * Note that we're avoiding the use of path.join as webpack and nodejs
 * want relative paths that start with ./ explicitly.
 *
 * In addition we mimic the VPATH style functionality of GNU Makefile
 * where we first check builddir, and then srcdir.
 */

function vpath(/* ... */) {
    var filename = Array.prototype.join.call(arguments, path.sep);
    var expanded = builddir + path.sep + filename;
    if (fs.existsSync(expanded))
        return expanded;
    expanded = srcdir + path.sep + filename;
    return expanded;
}

class Po2JSONPlugin {
    apply(compiler) {
        compiler.plugin('emit', function(compilation, callback) {
            const files = glob.sync('../po/*.po');
            files.forEach(function(file) {
                const dataFileName = `po.${/([^/]*).po$/.exec(file)[1]}.js`;
                const data = `cockpit.locale(${JSON.stringify(po2json.parseFileSync(file))});`;
                compilation.assets[dataFileName] = {
                    source: function() {
                        return data;
                    },
                    size: function() {
                        return data.length;
                    },
                };
            });
            callback();
        });
    }
}

/* Qualify all the paths in entries */
Object.keys(info.entries).forEach(function(key) {
    if (section && key.indexOf(section) !== 0) {
        delete info.entries[key];
        return;
    }

    info.entries[key] = info.entries[key].map(function(value) {
        if (value.indexOf("/") === -1)
            return value;
        else
            return vpath(value);
    });
});

/* Qualify all the paths in files listed */
var files = [];
info.files.forEach(function(value) {
    if (!section || value.indexOf(section) === 0)
        files.push({ from: vpath("src", value), to: value });
});
info.files = files;

var plugins = [
    new webpack.DefinePlugin({
        'process.env': {
            'NODE_ENV': JSON.stringify(production ? 'production' : 'development')
        }
    }),
    new copy(info.files),
    new Po2JSONPlugin(),
    new miniCssExtractPlugin({ filename: "[name].css" }),
    new ESLintPlugin({ extensions: ["js", "jsx"], exclude: ["spec", "node_modules", "src/lib"] }),
];

if (!production) {
    /* copy jasmine files over */
    plugins.unshift(new copy([
        {
            from: './spec/dbus/override.json',
            to: 'override.json'
        },
        {
            from: './spec/dbus/DBusSpecRunner.html',
            to: 'DBusSpecRunner.html'
        },
        {
            from: './node_modules/jasmine-core/lib/jasmine-core/jasmine.css',
            to: 'jasmine/jasmine.css'
        },
        {
            from: './node_modules/jasmine-core/lib/jasmine-core/jasmine.js',
            to: 'jasmine/jasmine.js',
        },
        {
            from: './node_modules/jasmine-core/lib/jasmine-core/jasmine-html.js',
            to: 'jasmine/jasmine-html.js'
        },
        {
            from: './node_modules/jasmine-core/lib/jasmine-core/boot.js',
            to: 'jasmine/boot.js'
        }
    ]));
}

/* Only minimize when in production mode */
if (production) {
    /* Rename output files when minimizing */
    output.filename = "[name].min.js";

    plugins.unshift(new CompressionPlugin({
        test: /\.(js|html)$/,
        minRatio: 0.9,
        deleteOriginalAssets: true
    }));
}

module.exports = {
    mode: production ? 'production' : 'development',
    entry: info.entries,
    resolve: {
        modules: [ nodedir, libdir ],
        alias: { 'font-awesome': path.resolve(nodedir, 'font-awesome-sass/assets/stylesheets') },
    },
    resolveLoader: {
        modules: [ nodedir, libdir ],
    },
    externals: externals,

    output: output,
    devtool: production ? false : "source-map",
    module: {
        rules: [
            {
                exclude: /node_modules/,
                use: "babel-loader",
                test: /\.(js|jsx)$/
            },
            /* HACK: remove unwanted fonts from PatternFly's css */
            /* The following rule will bundle the patternfly-cockpit.scss file included from index.js */
            /* Since Patternfly 4 includes more fonts than we are interested in do some fonts filtering here */
            {
                test: /patternfly-cockpit.scss$/,
                use: [
                    miniCssExtractPlugin.loader,
                    {
                        loader: 'css-loader',
                        options: {
                            sourceMap: true,
                            url: false,
                        },
                    },
                    {
                        loader: 'string-replace-loader',
                        options: {
                            multiple: [
                                {
                                    search: /src:url[(]"patternfly-icons-fake-path\/glyphicons-halflings-regular[^}]*/g,
                                    replace: 'font-display:block; src:url("../base1/fonts/glyphicons.woff") format("woff");',
                                },
                                {
                                    search: /src:url[(]"patternfly-fonts-fake-path\/PatternFlyIcons[^}]*/g,
                                    replace: 'src:url("../base1/fonts/patternfly.woff") format("woff");',
                                },
                                {
                                    search: /src:url[(]"patternfly-fonts-fake-path\/fontawesome[^}]*/,
                                    replace: 'font-display:block; src:url("../base1/fonts/fontawesome.woff?v=4.2.0") format("woff");',
                                },
                                {
                                    search: /src:url\("patternfly-icons-fake-path\/pficon[^}]*/g,
                                    replace: 'src:url("../base1/fonts/patternfly.woff") format("woff");',
                                },
                                {
                                    search: /@font-face[^}]*patternfly-fonts-fake-path[^}]*}/g,
                                    replace: '',
                                },
                            ]
                        },
                    },
                    {
                        loader: 'sass-loader',
                        options: {
                            sassOptions: {
                                includePaths: [
                                    // Teach webpack to resolve these references in order to build PF3 scss
                                    path.resolve(nodedir, 'font-awesome-sass', 'assets', 'stylesheets'),
                                    path.resolve(nodedir, 'patternfly', 'dist', 'sass'),
                                    path.resolve(nodedir, 'bootstrap-sass', 'assets', 'stylesheets'),
                                ],
                                outputStyle: 'compressed',
                            },
                            sourceMap: true,
                        },
                    },
                ]
            },
            /* This rule will handle scss and css stylesheets apart from pattenrfly-cockpit.scss which is handled just above */
            {
                test: /\.s?css$/,
                exclude: /patternfly-cockpit.scss/,
                use: [
                    miniCssExtractPlugin.loader,
                    {
                        loader: 'css-loader',
                        options: {
                            sourceMap: true,
                            url: false
                        }
                    },
                    {
                        loader: 'sass-loader',
                        options: {
                            sourceMap: true,
                            sassOptions: {
                                outputStyle: 'compressed',
                            }
                        }
                    },
                ]
            },
        ]
    },
    plugins: plugins
};
