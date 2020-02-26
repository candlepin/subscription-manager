const path = require("path");
const copy = require("copy-webpack-plugin");
const fs = require("fs");
const webpack = require("webpack");
const CompressionPlugin = require("compression-webpack-plugin");
const ExtractTextPlugin = require("extract-text-webpack-plugin");
const glob = require("glob");
const po2json = require("po2json");

var externals = {
    "cockpit": "cockpit",
};

/* These can be overridden, typically from the Makefile.am */
const srcdir = (process.env.SRCDIR || __dirname) + path.sep + "src";
const builddir = (process.env.SRCDIR || __dirname);
const distdir = builddir + path.sep + "dist";
const section = process.env.ONLYDIR || null;
const nodedir = path.resolve((process.env.SRCDIR || __dirname), "node_modules");

/* A standard nodejs and webpack pattern */
var production = process.env.NODE_ENV === 'production';

var info = {
    entries: {
        "index": [
            "./index.js",
            "./subscriptions.css",
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
    new webpack.ProvidePlugin({
        '$': 'jquery',
        'jQuery': 'jquery',
    }),
    new ExtractTextPlugin("subscriptions.css"),
    new Po2JSONPlugin(),
    new ExtractTextPlugin("[name].css")
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
    plugins.unshift(new webpack.optimize.UglifyJsPlugin({
        beautify: true,
        compress: {
            warnings: false
        },
    }));

    /* Rename output files when minimizing */
    output.filename = "[name].min.js";

    plugins.unshift(new CompressionPlugin({
        asset: "[path].gz[query]",
        test: /\.(js|html)$/,
        minRatio: 0.9,
        deleteOriginalAssets: true
    }));
}

module.exports = {
    entry: info.entries,
    externals: externals,
    output: output,
    devtool: production ? false : "source-map",
    module: {
        rules: [
            {
                enforce: 'pre',
                exclude: /node_modules/,
                loader: 'jshint-loader',
                test: /\.js$/
            },
            {
                enforce: 'pre',
                exclude: /node_modules/,
                loader: 'eslint-loader',
                test: /\.jsx$/
            },
            {
                enforce: 'pre',
                exclude: /node_modules/,
                loader: 'jshint-loader',
                test: /\.es6$/
            },
            {
                exclude: /node_modules/,
                loader: 'babel-loader',
                test: /\.js$/
            },
            {
                exclude: /node_modules/,
                loader: 'babel-loader',
                test: /\.jsx$/
            },
            {
                exclude: /node_modules/,
                loader: 'babel-loader',
                test: /\.es6$/
            },
            {
                exclude: /node_modules/,
                use: ExtractTextPlugin.extract({
                    fallback: "style-loader",
                    use: {
                        loader: "css-loader",
                        options: { minimize: production },
                    },
                }),
                test: /\.css$/
            },
            {
                test: /\.(png|jpg|jpeg|gif|svg|woff|woff2|eot|ttf|wav|mp3)$/,
                options: {
                    name: '[path][name].[ext]'
                },
                loader: 'file-loader',
            },
            {
                test: /\.less$/,
                loader: ExtractTextPlugin.extract("css-loader?sourceMap&minimize=!less-loader?sourceMap&compress=false")
            },
        ]
    },
    plugins: plugins
};
